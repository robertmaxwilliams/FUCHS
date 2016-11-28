#! /usr/bin/env python


# script to evaluate circle splicing variants

def read_circle_file(infile):
    I = open(infile)
    circ_table = []
    for line in I:
        circle_id = line.split('\t')[0]
        chromosome = circle_id.split(':')[0]
        start = int(circle_id.split(':')[1].split('|')[0])
        end = int(circle_id.split(':')[1].split('|')[1])
        circ_table += [(chromosome, start, end)]
    I.close()
    return (circ_table)


def annotate_circles(circles, bed_annotation, platform, split_character):
    annotated_circles = {}
    bed = pybedtools.example_bedtool(bedfile)
    for c in circles:
        annotated_circles[c] = []
        coordinates = pybedtools.BedTool('%s %s %s' % (c[0], c[1], c[2]), from_string=True)
        transcripts = bed.intersect(coordinates)
        for t in transcripts:
            if platform == 'refseq':
                tname = split_character.join(t[3].split(split_character)[0:2])
            else:
                tname = t[3].split(split_character)[0]
            annotated_circles[c] += [tname]
        annotated_circles[c] = set(annotated_circles[c])
    return (annotated_circles)


def accumulate_over_transcripts(circles):
    transcripts = {}
    for c in circles:
        for t in circles[c]:
            if not t in transcripts:
                transcripts[t] = []
            transcripts[t] += [c]
    return (transcripts)


def classify_multi_circle_transcripts(transcripts):
    classification = {}
    for lola in transcripts:
        types = {'same_start': {}, 'same_end': {}, 'within': {}, 'overlapping': {}, 'circles': []}
        circles = sorted(transcripts[lola])
        for i, circle1 in enumerate(circles):
            types['circles'] += ['%s:%s-%s' % (circle1[0], circle1[1], circle1[2])]
            for j, circle2 in enumerate(circles):
                if i < j:
                    if circle1[1] == circle2[1]:
                        if not circle1[1] in types['same_start']:
                            types['same_start'][circle1[1]] = []
                        types['same_start'][circle1[1]] += ['%s:%s-%s' % (circle1[0], circle1[1], circle1[2]),
                                                            '%s:%s-%s' % (circle2[0], circle2[1], circle2[2])]
                    elif circle1[2] == circle2[2]:
                        if not circle1[2] in types['same_end']:
                            types['same_end'][circle1[2]] = []
                        types['same_end'][circle1[2]] += ['%s:%s-%s' % (circle1[0], circle1[1], circle1[2]),
                                                          '%s:%s-%s' % (circle2[0], circle2[1], circle2[2])]
                    elif (circle1[1] < circle2[1] and circle1[2] > circle2[2]) or (
                            circle1[1] > circle2[1] and circle1[2] < circle2[2]):
                        if not i in types['within']:
                            types['within'][i] = []
                        types['within'][i] += ['%s:%s-%s' % (circle1[0], circle1[1], circle1[2]),
                                               '%s:%s-%s' % (circle2[0], circle2[1], circle2[2])]
                    elif (circle1[1] < circle2[1] and circle1[2] < circle2[2] and circle1[2] > circle2[1]) or (
                                circle1[1] > circle2[1] and circle1[2] > circle2[2] and circle1[1] < circle2[2]):
                        if not i in types['overlapping']:
                            types['overlapping'][i] = []
                        types['overlapping'][i] += ['%s:%s-%s' % (circle1[0], circle1[1], circle1[2]),
                                                    '%s:%s-%s' % (circle2[0], circle2[1], circle2[2])]
        classification[lola] = types
    return (classification)


def write_genes(types, outfile):
    O = open(outfile, 'w')
    O.write('Transcript\tcircles\tsame_start\tsame_end\toverlapping\twithin\n')
    for lola in types:
        O.write('%s\t%s' % (lola, ','.join(types[lola]['circles'])))
        if len(types[lola]['same_start']) == 0:
            O.write('\t.')
        elif len(types[lola]['same_start']) > 0:
            O.write('\t')
            for circ in types[lola]['same_start']:
                O.write('%s,' % ('|'.join(set(types[lola]['same_start'][circ]))))
        if len(types[lola]['same_end']) == 0:
            O.write('\t.')
        elif len(types[lola]['same_end']) > 0:
            O.write('\t')
            for circ in types[lola]['same_end']:
                O.write('%s,' % ('|'.join(set(types[lola]['same_end'][circ]))))
        if len(types[lola]['overlapping']) == 0:
            O.write('\t.')
        elif len(types[lola]['overlapping']) > 0:
            O.write('\t')
            for circ in types[lola]['overlapping']:
                O.write('%s,' % ('|'.join(set(types[lola]['overlapping'][circ]))))
        if len(types[lola]['within']) == 0:
            O.write('\t.')
        elif len(types[lola]['within']) > 0:
            O.write('\t')
            for circ in types[lola]['within']:
                O.write('%s,' % ('|'.join(set(types[lola]['within'][circ]))))
        O.write('\n')
    O.close()
    return


# run program
if __name__ == '__main__':
    # needed packages
    import argparse
    import pybedtools
    import tempfile

    parser = argparse.ArgumentParser(description='Detect genes with different forms of circles')

    # input
    parser.add_argument('circlefile', metavar='circIDS.txt',
                        help='Tabseparated file of circle coordinates formated as chr:start|end. One circle per line')
    parser.add_argument('bedfile', metavar='annotation.bed', help='Annotation in bed format')
    # output
    parser.add_argument('outfile', metavar='outfile', help='File to write genes giving rise to different circles to')
    # options
    parser.add_argument('-s', dest='split_character', default='_', help='feature name separator.')
    parser.add_argument('-p', dest='ref_platform', default='refseq',
                        help='specifies the annotation platform which was used (refseq or ensembl)')
    parser.add_argument('--tmp', dest='tmp_folder', default='.',
                        help='tempfolder to store tempfiles generated by pybedtools.')

    args = parser.parse_args()

    # parse arguments
    circlefile = args.circlefile
    bedfile = args.bedfile
    outfile = args.outfile
    split_character = args.split_character
    platform = args.ref_platform
    tmp_folder = args.tmp_folder

    # set temp folder
    tempfile.tempdir = tmp_folder

    # run
    circles = read_circle_file(circlefile)
    annotated_circles = annotate_circles(circles, bedfile, platform, split_character)
    transcripts = accumulate_over_transcripts(annotated_circles)
    circle_types = classify_multi_circle_transcripts(transcripts)
    write_genes(circle_types, outfile)
