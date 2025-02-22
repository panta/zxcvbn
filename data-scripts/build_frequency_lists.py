#!/usr/bin/python
import os
import sys
import time
import codecs

from operator import itemgetter

def usage():
    return '''
usage:
%s data-dir frequency_lists.coffee

generates frequency_lists.coffee (zxcvbn's ranked dictionary file) from word frequency data.
data-dir should contain frequency counts, as generated by the data-scripts/count_* scripts.

DICTIONARIES controls which frequency data will be included and at maximum how many tokens
per dictionary.

If a token appears in multiple frequency lists, it will only appear once in emitted .coffee file,
in the dictionary where it has lowest rank.

Short tokens, if rare, are also filtered out. If a token has higher rank than 10**(token.length),
it will be excluded because a bruteforce match would have given it a lower guess score.

A warning will be printed if DICTIONARIES contains a dictionary name that doesn't appear in
passed data dir, or vice-versa.
    ''' % sys.argv[0]

# maps dict name to num words. None value means "include all words"
DICTIONARIES = dict(
    us_tv_and_film    = 30000,
    english_wikipedia = 30000,
    passwords         = 30000,
    surnames          = 10000,
    male_names        = None,
    female_names      = None,
    italian_words     = 30000,
)

# returns {list_name: {token: rank}}, as tokens and ranks occur in each file.
def parse_frequency_lists(data_dir):
    freq_lists = {}
    for filename in os.listdir(data_dir):
        freq_list_name, ext = os.path.splitext(filename)
        if freq_list_name not in DICTIONARIES:
            msg = 'Warning: %s appears in %s directory but not in DICTIONARY settings. Excluding.'
            print(msg % (freq_list_name, data_dir))
            continue
        token_to_rank = {}
        with codecs.open(os.path.join(data_dir, filename), 'r', 'utf8') as f:
            for i, line in enumerate(f):
                rank = i + 1 # rank starts at 1
                token = line.split()[0]
                token_to_rank[token] = rank
        freq_lists[freq_list_name] = token_to_rank
    for freq_list_name in DICTIONARIES:
        if freq_list_name not in freq_lists:
            msg = 'Warning: %s appears in DICTIONARY settings but not in %s directory. Excluding.'
            print(msg % (freq_list_name, data_dir))
    return freq_lists

def is_rare_and_short(token, rank):
    return rank >= 10**len(token)

def has_comma_or_double_quote(token, rank, lst_name):
    # hax, switch to csv or similar if this excludes too much.
    # simple comma joining has the advantage of being easy to process
    # client-side w/o needing a lib, and so far this only excludes a few
    # very high-rank tokens eg 'ps8,000' at rank 74868 from wikipedia list.
    if ',' in token or '"' in token:
        return True
    return False

def filter_frequency_lists(freq_lists):
    '''
    filters frequency data according to:
        - filter out short tokens if they are too rare.
        - filter out tokens if they already appear in another dict
          at lower rank.
        - cut off final freq_list at limits set in DICTIONARIES, if any.
    '''
    filtered_token_and_rank = {} # maps {name: [(token, rank), ...]}
    token_count = {}             # maps freq list name: current token count.
    for name in freq_lists:
        filtered_token_and_rank[name] = []
        token_count[name] = 0
    minimum_rank = {} # maps token -> lowest token rank across all freq lists
    minimum_name = {} # maps token -> freq list name with lowest token rank
    for name, token_to_rank in freq_lists.items():
        for token, rank in token_to_rank.items():
            if token not in minimum_rank:
                assert token not in minimum_name
                minimum_rank[token] = rank
                minimum_name[token] = name
            else:
                assert token in minimum_name
                assert minimum_name[token] != name, 'same token occurs multiple times in %s' % name
                min_rank = minimum_rank[token]
                if rank < min_rank:
                    minimum_rank[token] = rank
                    minimum_name[token] = name
    for name, token_to_rank in freq_lists.items():
        for token, rank in token_to_rank.items():
            if minimum_name[token] != name:
                continue
            if is_rare_and_short(token, rank) or has_comma_or_double_quote(token, rank, name):
                continue
            filtered_token_and_rank[name].append((token, rank))
            token_count[name] += 1
    result = {}
    for name, token_rank_pairs in filtered_token_and_rank.items():
        token_rank_pairs.sort(key=itemgetter(1))
        cutoff_limit = DICTIONARIES[name]
        if cutoff_limit and len(token_rank_pairs) > cutoff_limit:
            token_rank_pairs = token_rank_pairs[:cutoff_limit]
        result[name] = [pair[0] for pair in token_rank_pairs] # discard rank post-sort
    return result

def to_kv(lst, lst_name):
    val = ', '.join('"%s"' % l.replace('"', '\\"').replace('\\', '\\\\') for l in lst)
    return '\t"%s": {%s},' % (lst_name, val)

def main():
    if len(sys.argv) != 3:
        print(usage())
        sys.exit(0)
    data_dir, output_file = sys.argv[1:]
    unfiltered_freq_lists = parse_frequency_lists(data_dir)
    freq_lists = filter_frequency_lists(unfiltered_freq_lists)
    with codecs.open(output_file, 'w', 'utf8') as f:
        script_name = os.path.split(sys.argv[0])[1]
        f.write('// +build !no_embedded_dict\n\n')
        f.write('package frequency // generated by %s\n\n' % script_name)
        f.write('var FrequencyLists = map[string][]string {\n')
        lines = []
        for name, lst in freq_lists.items():
            lines.append(to_kv(lst, name))
        f.write('\n  '.join(lines))
        f.write('\n}\n')

if __name__ == '__main__':
    main()
