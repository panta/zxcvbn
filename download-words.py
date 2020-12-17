#!/usr/bin/env python

import io
from contextlib import closing
import requests # $ pip install requests
import re
import json


WORDS_URL = 'https://raw.githubusercontent.com/hermitdave/FrequencyWords/master/content/2016/it/it_full.txt'


def main():
    words = []
    word_count_re = re.compile(r'(\w+)\s+([0-9]+)')
    r = requests.get(WORDS_URL)
    with closing(r), io.BytesIO(r.content) as f:
        for line in f.readlines():
            str_line = str(line,'utf-8').strip()
            m = word_count_re.match(str_line)
            if m:
                word = m[1]
                count = int(m[2])
                words.append((word, count))
                # print("word:{} count:{}".format(m[1], m[2]))
    with open("data/italian_words.json", "w") as write_file:
        for word_count in words:
            (word, count) = word_count
            write_file.write("{:18} {}\n".format(word, count))
    # with open("data/data/Italian.json", "w") as write_file:
    #     json.dump(dict(List=words), write_file)

if __name__ == '__main__':
    main()
