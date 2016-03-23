# python script to get coverage profile for circle

import os
import argparse
import pybedtools
import tempfile

parser = argparse.ArgumentParser(description='')

# input
parser.add_argument('bedfile', metavar = 'feature.bed', help = 'bed formatted feature file including exons.' )
parser.add_argument('inputfolder', metavar = 'folder', help = 'folder containing all circle bam files. (full path, but without sample name)')
parser.add_argument('sample', metavar = 'sample_name', help = 'sample_name to title every thing.')
# options
parser.add_argument('-e', dest = 'exon_index', default = 3, type = int, help = 'field indicating the exon number after splitting feature name.')
parser.add_argument('-s', dest = 'split_character', default = '_', help = 'feature name separator.')
parser.add_argument('-p', dest = 'ref_platform', default = 'refseq', help = 'specifies the annotation platform which was used (refseq or ensembl)')

args = parser.parse_args()

# parse arguments
bedfile = args.bedfile
inputfolder = args.inputfolder 
sample = args.sample
exon_index = args.exon_index
split_character = args.split_character
platform = args.ref_platform

# include some checks to make sure input was provided correctly


# define functions

def circle_exon_count(bamfile2, bedfile, exon_index, split_character, platform): # does what I think it does, adjust to collapse different transcripts from the same gene, choose transcript describing the circle best
    '''
    '''
    x = pybedtools.example_bedtool(bamfile2)
    b = pybedtools.example_bedtool(bedfile)
    y = x.intersect(b, bed = True, wo = True, split = True)
    transcripts = {}
    found_features = []
    for hit in y:
	found_features += [hit[15]]
	transcript = hit[15]
	start = int(hit[13])
	end = int(hit[14])
	length = end - start
	strand_read = hit[5]
	strand_feature = hit[17]
	if platform == 'refseq':
	    transcript_id = split_character.join(transcript.split(split_character)[0:2])
	elif platform == 'ensembl':
	    transcript_id = transcript.split(split_character)[0]
	else:
	    transcript_id = 'NA'
	    print('you are using an unkown annotation platform, please use refseq or ensembl')
	exon = int(transcript.split(split_character)[exon_index])
	read = hit[3]
	chromosome = hit[0]
	if not transcript_id in transcripts:
	    transcripts[transcript_id] = {}
	if not exon in transcripts[transcript_id]:
	    transcripts[transcript_id][exon] = {'length': length , 'start': start, 'end': end, 'strand_read': [], 'strand_feature': strand_feature, 'reads': [], 'chromosome': chromosome}
	transcripts[transcript_id][exon]['reads'] += [read]
	transcripts[transcript_id][exon]['strand_read'] += [strand_read]
    return(transcripts, found_features)

def write_exon_count(outfile, exon_count, sample, circle_id, transcript): #append to existing exon_count file for the sample
    '''
    '''
    out = open(outfile, 'a')
    # sample\tcircle_id\ttranscript_id\texon_id\tchr\tstart\tend\tstrand\texon_length\tunique_reads\tfragments\tnumber+\tnumber-\n
    # sort exon ids per transcript..and then iterate from min to max, if one exon isn't in it, fill with 0's, identify potentially skipped exons
    for t in exon_count:
	if t == transcript:
	    for exon in range(min(exon_count[transcript]), (max(exon_count[transcript])+1)):
		if exon in exon_count[transcript]:
		    num_plus = exon_count[transcript][exon]['strand_read'].count('+')
		    num_minus = exon_count[transcript][exon]['strand_read'].count('-')
		    unique_reads = set([w.split('/')[0] for w in exon_count[transcript][exon]['reads']])
		    out.write('%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n' %(sample, circle_id, transcript, ','.join(exon_count.keys()), exon, exon_count[transcript][exon]['chromosome'], exon_count[transcript][exon]['start'], exon_count[transcript][exon]['end'], exon_count[transcript][exon]['strand_feature'], exon_count[transcript][exon]['length'], len(unique_reads), len(exon_count[transcript][exon]['reads']), num_plus, num_minus))
		else:
		    out.write('%s\t%s\t%s\t%s\t%s\t0\t0\t0\t0\t0\t0\t0\t0\t0\n' %(sample, circle_id, transcript, ','.join(exon_count.keys()), exon))
    return


def filter_features(bed_features, feature_names):
    '''
    '''
    intervals = []
    for interval in bed_features:
	if interval[3] in feature_names:
	    intervals += [interval]
    return(intervals)

def choose_transcript(exon_counts):
    '''
    '''
    if len(exon_counts) > 0:
        transcript = exon_counts.keys()[0]
        missing_exons_transcript = 100
        for t in exon_counts:
	    missing_exons = 0
	    for e in range(min(exon_counts[t]), max(exon_counts[t])+1):
		if not e in exon_counts[t]:
		    missing_exons += 1
            if len(exon_counts[t]) > len(exon_counts[transcript]):
                transcript = t
                missing_exons_transcript = missing_exons
            elif missing_exons < missing_exons_transcript:
		transcript = t
		missing_exons_transcript = missing_exons
            elif 'NR' in transcript and 'NM' in t:
                transcript = t
                missing_exons_transcript = missing_exons
    else:
        transcript = ''
    return(transcript)


def circle_coverage_profile(bamfile, bedfile, exon_ind, split_character, platform):
    '''
    '''
    x = pybedtools.example_bedtool(bamfile)
    y = x.coverage(bedfile, d = True, split = True)
    transcriptwise_coverage = {}
    for position in y:
	if platform == 'refseq':
	    transcript = split_character.join(position[3].split(split_character)[0:2])
	elif platform == 'ensembl':
	    transcript = position[3].split(split_character)[0]
	else:
	    transcript = 'NA'
	    print('you are using an unknown annotation platform, please use refseq or ensembl like formats')
	exon = int(position[3].split(split_character)[exon_ind])
	if not transcript in transcriptwise_coverage:
	    transcriptwise_coverage[transcript] = {}
	if not exon in transcriptwise_coverage[transcript]:
	    transcriptwise_coverage[transcript][exon] = {'relative_positions': [], 'position_coverage' : [], 'chromosome': position[0], 'start': position[1], 'end': position[2]}
	transcriptwise_coverage[transcript][exon]['position_coverage'] += [position[7]]
	transcriptwise_coverage[transcript][exon]['relative_positions'] += [position[6]]
    return(transcriptwise_coverage)

def write_coverage_profile(inputfolder, coverage_profile, sample, circle_id, transcript):
    '''
    '''
    for t in coverage_profile:
	if t == transcript:
	    out = open('%s/%s.coverage_profiles/%s.%s.txt' %(inputfolder, sample, circle_id, transcript), 'w')
	    out.write('exon\trelative_pos_in_circle\trelative_pos_in_exon\tcoverage\n')
	    pos_in_circle = 1
	    for exon in range(min(coverage_profile[transcript]), (max(coverage_profile[transcript])+1)):
		if exon in coverage_profile[transcript]:
		    for i, position in enumerate(coverage_profile[transcript][exon]['relative_positions']):
			out.write('%s\t%s\t%s\t%s\n' %(exon, pos_in_circle, position, coverage_profile[transcript][exon]['position_coverage'][i]))
			pos_in_circle += 1
		else:
		    for i, position in enumerate(range(0,50)):
			out.write('%s\t%s\t%s\t0\n' %(exon, pos_in_circle, position))
			pos_in_circle += 1
    out.close()
    return

def format_to_bed12(exon_count, transcript, circle_id, number_of_reads, outfile):
    bed12 = {}
    for t in exon_count:
	if t == transcript:
	    bed12['01_chrom'] = circle_id.split('_')[0]
	    bed12['02_start'] = circle_id.split('_')[1]
	    bed12['03_end'] = circle_id.split('_')[2]
	    bed12['04_name'] = t
	    bed12['05_score'] = '%s' % (number_of_reads)
	    bed12['06_strand'] = '.'
	    bed12['07_thick_start'] = circle_id.split('_')[1]
	    bed12['08_thick_end'] = circle_id.split('_')[2]
	    bed12['09_itemRGB'] = '0,255,0'
	    bed12['10_blockCount'] = '%s' %(len(exon_count[t]))
	    bed12['11_block_sizes'] = []
	    bed12['12_block_starts'] = []
	    for e in sorted(exon_count[t]):
		bed12['06_strand'] = exon_count[t][e]['strand_feature']
		bed12['11_block_sizes'] += ['%s' %(exon_count[t][e]['length']-1)]
		bed12['12_block_starts'] += ['%s' %(exon_count[t][e]['start']+1)]
	    bed12['12_block_starts'] = ','.join(bed12['12_block_starts'])
	    bed12['11_block_sizes'] = ','.join(bed12['11_block_sizes'])
    Bed12 = []
    for i in sorted(bed12):
	Bed12 += [bed12[i]]
    o = open(outfile, 'a')
    o.write('%s\n' %('\t'.join(Bed12)))
    o.close()
    return

# circle exon count over all bam files in sample folder, this could easily be parralellised


tempfile.tempdir = '/beegfs/group_dv/home/FMetge/tmp'

# initializing the result table file
exon_count_file = '%s/%s.exon_counts.txt' %(inputfolder, sample)
exon_counts_out = open(exon_count_file, 'w')
exon_counts_out.write('sample\tcircle_id\ttranscript_id\tother_ids\texon_id\tchr\tstart\tend\tstrand\texon_length\tunique_reads\tfragments\tnumber+\tnumber-\n')
exon_counts_out.close()

# all circle files in a given folder
files = os.listdir('%s/%s' %(inputfolder, sample))

# create folder for coverage profiles
folders = os.listdir(inputfolder)
print(folders)
if not '%s.coverage_profiles' %(sample) in folders:
    os.mkdir('%s/%s.coverage_profiles' %(inputfolder, sample))

# iterate over all files
for f in files:
    # only consider sorted bam files
    if f.split('.')[-2] == 'sorted':
	# extract circle id from filename, works for files generated by extract_reads.py, consider making this more flexible
	circle_id = '%s_%s_%s' %(f.split('_')[0], f.split('_')[1], f.split('_')[2])
	number_of_reads = int(f.split('_')[3].split('.')[0]. replace('reads', ''))
	bamfile2 = '%s/%s/%s' %(inputfolder, sample, f)
	# open bed feature file
	b = pybedtools.example_bedtool(bedfile)
	# get read counts for each exon in circle
	exon_counts, found_features = circle_exon_count(bamfile2, bedfile, exon_index, split_character, platform)
	# choose best fitting transcript
	print(exon_counts.keys())
	transcript_id = choose_transcript(exon_counts)
	# add circle to result table
	write_exon_count(exon_count_file, exon_counts, sample, circle_id, transcript_id)
	format_to_bed12(exon_counts, transcript_id, circle_id, number_of_reads, '%s/%s.exon_counts.bed' %(inputfolder, sample))
	filtered_features = filter_features(b, found_features)
	print('.')
	if len(filtered_features) > 0:
	    coverage_track = circle_coverage_profile(bamfile2, filtered_features, exon_index, split_character, platform)
	    write_coverage_profile(inputfolder, coverage_track, sample, circle_id, transcript_id)


## make pictures using rscript

#### test area
#bedfile = '/home/fmetge/Documents/work/Annotations/hg38/hg38.RefSeq.exons.bed'
#bamfile = '/home/fmetge/Documents/work/circRNA/exon_usage/test_outputfolder/MiSeq_A_300BP/2_199368605_199433514_7reads.sorted.bam'
#bamfile = '/home/fmetge/Documents/work/circRNA/exon_usage/test_outputfolder/MiSeq_A_300BP/10_87223718_87355425_9reads.sorted.bam'


#x = pybedtools.example_bedtool(bamfile)
#bedfile = '/home/fmetge/Documents/work/Annotations/hg38/hg38.RefSeq.exons.bed'
#bamfile = '/home/fmetge/Documents/work/circRNA/FUCHS/testdata/output/test_20160106/12_1236769_1290012_12reads.sorted.bam'
#b = pybedtools.example_bedtool(bedfile)
#exon_counts, found_features = circle_exon_count(bamfile, bedfile, 3, '_')

#filtered_features = filter_features(b, found_features)
##y = x.coverage(filtered_features, d = True)

#coverage_track = circle_coverage_profile(bamfile, filtered_features, 3)


