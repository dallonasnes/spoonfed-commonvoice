import csv
import json
import os
import os.path
from shutil import copyfile
from typing import List
import urllib.request
import urllib.parse
from collections import OrderedDict
import string
import argparse
from tqdm import tqdm


ANKI_MEDIA_PATH = "/".join(os.getcwd().split('/')[0:3]) + "/Library/Application Support/Anki2/User 1/collection.media/"

""" This section copied from sample code here: https://github.com/FooSoft/anki-connect"""
def request(action, **params):
    return {'action': action, 'params': params, 'version': 6}

def invoke(action, **params):
    requestJson = json.dumps(request(action, **params)).encode('utf-8')
    response = json.load(urllib.request.urlopen(urllib.request.Request('http://localhost:8765', requestJson)))
    if len(response) != 2:
        raise Exception('response has an unexpected number of fields')
    if 'error' not in response:
        raise Exception('response is missing required error field')
    if 'result' not in response:
        raise Exception('response is missing required result field')
    if response['error'] is not None:
        raise Exception(response['error'])
    return response['result']
"""End section copied from anki-connect github"""

def _filter_out_punctuation(sentence):
    cleansed_sentence = '%s' % sentence # copy the same string
    for word in sentence.split():
        if word in string.punctuation or word in ['،', '؟']:
            cleansed_sentence = cleansed_sentence.replace(word, '').strip()
    return cleansed_sentence.strip()

def build_audio_path_to_sentence_map(args):
    data_map = {}
    is_validated_file = "validated" in args.tsv.lower()
    with open(args.tsv) as csv_file:
        csv_reader = csv.reader(csv_file, delimiter='\t')
        line_count = 0
        for row in csv_reader:
            if line_count == 0:
                # ignore header row
                line_count += 1
            else:
                audio_path = row[1]
                sentence = _filter_out_punctuation(row[2])
                up_votes = row[3]
                down_votes = row[4]
                if is_validated_file or (up_votes > 0 and down_votes == 0):
                    data_map[audio_path] = sentence
    return data_map

def format_google_translate_query(sentence, lang_code):
    url_encoded_sentence = urllib.parse.quote(sentence)
    url = "https://translate.google.com/?sl={0}&tl=en&text={1}&op=translate".format(lang_code, url_encoded_sentence)
    return url


def _get_cloze_for_sentence(sentence, word_freq_map):
    # find least frequent word in sentence and make it a cloze
    word_freqs = {}
    for word in sentence.split():
        word_freqs[word] = word_freq_map[word.strip().lower()]
    # return key of word_freqs which has min value
    least_freq_word, _ = min(word_freqs.items(), key=lambda x: x[1])
    cloze_sentence = sentence.replace(least_freq_word, '{{c1::' + least_freq_word + '}}')
    return cloze_sentence


def _build_word_frequency_map(sentences):
    data_map = {}
    for sentence in sentences:
        for word in sentence.split():
            word = word.strip().lower()
            if word in data_map:
                data_map[word] += 1
            else:
                data_map[word] = 1
    return data_map


def add_listening_notes_to_anki_connect(deck_name, audio_paths_ordered, data_map, lang_code):
    # note that if the note already exists, it won't be modified
    all_notes = []
    word_frequency_map = _build_word_frequency_map(list(audio_paths_ordered.values()))
    print("BEGINNING TO GENERATE LISTENING NOTES FROM SENTENCES")
    for audio_path in tqdm(audio_paths_ordered):
        sentence = data_map[audio_path]
        note = {
                "deckName": deck_name,
                "modelName": "CommonVoice cloze note",
                "fields": {
                    "Audio": '[sound:{0}]'.format(audio_path),
                    "Sentence": _get_cloze_for_sentence(sentence, word_frequency_map),
                    "Translate Link": format_google_translate_query(sentence, lang_code)
                }
            }
        all_notes.append(note)
  
    print("COMPLETED GENERATING LISTENING NOTES FROM SENTENCES")
    print("BEGINNING SYNCING LISTENING NOTES TO ANKI")
    invoke('addNotes', notes=all_notes)
    print("FINISHED SYNCING LISTENING NOTES TO ANKI")

def add_reading_notes_to_anki_connect(deck_name, audio_paths_ordered, data_map, lang_code):
    # note that if the note already exists, it won't be modified
    all_notes = []
    print("BEGINNING TO GENERATE READING NOTES FROM SENTENCES")
    for audio_path in tqdm(audio_paths_ordered):
        sentence = data_map[audio_path]
        note = {
                "deckName": deck_name,
                "modelName": "CommonVoice note",
                "fields": {
                    "Sentence": sentence,
                    "Audio": '[sound:{0}]'.format(audio_path),
                    "Translate Link": format_google_translate_query(sentence, lang_code)
                }
            }
        all_notes.append(note)
  
    print("COMPLETED GENERATING READING NOTES FROM SENTENCES")
    print("BEGINNING SYNCING READING NOTES TO ANKI")
    invoke('addNotes', notes=all_notes)
    print("FINISHED SYNCING READING NOTES TO ANKI")

def copy_files_to_anki_store(relative_audio_paths: List, args):
    """
        For each audio file,
        first check if file exists in Anki store,
        if not then copy from local to there
    """
    print("COPYING FILES TO ANKI MEDIA STORE")
    for audio_name in tqdm(relative_audio_paths):
        dest_path = ANKI_MEDIA_PATH + audio_name
        if not os.path.isfile(dest_path):
            src_path = args.audio + audio_name
            copyfile(src_path, dest_path)
    print("FINISHED COPYING FILES TO ANKI MEDIA STORE")

def _invert_ordered_dict(map):
    # NB: CommonVoice has unique audio but many duplicate sentences
    # this method drastically reduces number of sentences by changing hash table key
    rtn_val = OrderedDict()
    for key, value in map.items():
        if value not in rtn_val:
            rtn_val[value] = key
    return rtn_val

def _is_new_word_misspelling_of_old_word(just_seen_words, previously_seen_words):
    """Compares the new word in the new sentence to each of the previously seen words
    If the new word is only one character off from any previous word, we assume it is a misspelling or pluralization
    """
    # TODO: this didn't work to distinguish kheyli from kheyli with arabic ys
    # compare current word to all previously seen words to check if just a misspelling
    # do this buy building map of char freq and if there is only one char diff then skip this one
    new_word = list(just_seen_words)[0]
    new_word_char_freq = {}
    for char in new_word:
        if char in new_word_char_freq:
            new_word_char_freq[char] += 1
        else:
            new_word_char_freq[char] = 1
    # filter down to words of the same length
    for previous_word in list(filter(lambda prev_word: len(prev_word) == len(new_word), previously_seen_words)):
        prev_word_char_freq = {}
        for char in previous_word:
            if char in prev_word_char_freq:
                prev_word_char_freq[char] += 1
            else:
                prev_word_char_freq[char] = 1
        # now subtract previous chars from new char map
        # if only one char remains in new char map, then skip this sentence
        # because the new word in the sentence is only one char different from the previous word
        for char in prev_word_char_freq.keys():
            if char in new_word_char_freq:
                new_word_char_freq[char] -= 1
        total_new_chars_in_new_word = sum(new_word_char_freq.values())
        if total_new_chars_in_new_word == 1:
            return True
    return False

def _order_sentences_by_min_num_new_words(sentences, min_sentence_length, max_card_count):
    sentences_ordered_by_num_new_words = []
    sentences_ordered_count = 0
    unused_sentences_init = sentences.copy()
    if min_sentence_length > 1:
        unused_sentences_unsorted = list(filter(lambda x: len(x.split()) >= min_sentence_length, unused_sentences_init))
        unused_sentences = sorted(unused_sentences_unsorted, key=len)
    previously_seen_words = set()
    print("BEGINNING TO APPLY ORDERING TO {0} SENTENCES".format(len(unused_sentences)))
    with tqdm(total=max_card_count) as pbar:
        while sentences_ordered_count < max_card_count and len(unused_sentences) > 0:
            sentence_new_word_count_map = {}
            already_popped_sentence = False
            for sentence in unused_sentences:
                new_word_count = 0
                just_seen_words = set()
                for word in sentence.split():
                    word = word.strip().lower()
                    if word not in previously_seen_words and word not in just_seen_words:
                        new_word_count += 1
                        just_seen_words.add(word)
                if new_word_count == 0:
                    # we found a sentence with zero new words, so we can get rid of it and keep going
                    idx = unused_sentences.index(sentence)
                    _ = unused_sentences.pop(idx)
                    already_popped_sentence = True
                    break #break out of for loop over unused_sentences
                elif new_word_count == 1:
                    # we found a sentence with exactly one new word
                    # if the new word likely isn't a misspelling, then add it
                    idx = unused_sentences.index(sentence)
                    sentence = unused_sentences.pop(idx)
                    
                    if not _is_new_word_misspelling_of_old_word(just_seen_words, previously_seen_words):
                        sentences_ordered_by_num_new_words.append(sentence)
                        sentences_ordered_count += 1
                        pbar.update(1)
                    for word in sentence.split():
                        word = word.strip().lower()
                        previously_seen_words.add(word)
                    already_popped_sentence = True
                    break #break out of for loop over unused_sentences
                else:
                    # need to get new_word_count of all unused_sentences
                    sentence_new_word_count_map[sentence] = new_word_count
            # now that we've checked all unused_sentences
            # we can find the sentence with min new words and add to list
            if not already_popped_sentence:
                # first find sentence with min new word score
                sentence, _ = min(sentence_new_word_count_map.items(), key=lambda x: x[1])
                idx = unused_sentences.index(sentence)
                sentence = unused_sentences.pop(idx)
                sentences_ordered_by_num_new_words.append(sentence)
                sentences_ordered_count += 1
                pbar.update(1)
                already_popped_sentence = True
                for word in sentence.split():
                    word = word.strip().lower()
                    previously_seen_words.add(word)
    
    print("FINISHED APPLYING ORDERING TO SENTENCES")
    return sentences_ordered_by_num_new_words        

def _build_map_audio_to_sentence_ordered_by_min_new_words_in_sentence(sentences_ordered_by_min_num_new_words, sentence_to_audio_map):
    rtn_val = OrderedDict()
    for sentence in sentences_ordered_by_min_num_new_words:
        audio_path = sentence_to_audio_map[sentence]
        rtn_val[audio_path] = sentence
    return rtn_val

def _order_sentences_by_num_new_words(deduped_ordered_map, min_sentence_length, max_card_count):
    sentence_to_audio_map = _invert_ordered_dict(deduped_ordered_map)
    sentences_ordered_by_min_num_new_words = _order_sentences_by_min_num_new_words(list(sentence_to_audio_map.keys()), min_sentence_length, max_card_count)
    map_audio_to_sentence_ordered_by_min_new_words_in_sentence = _build_map_audio_to_sentence_ordered_by_min_new_words_in_sentence(sentences_ordered_by_min_num_new_words, sentence_to_audio_map)
    return map_audio_to_sentence_ordered_by_min_new_words_in_sentence

def apply_ordering_to_notes(data_map, min_sentence_length, max_card_count):
    # order map by length of each sentence
    ordered_map = OrderedDict(sorted(data_map.items(), key=lambda t: len(t[1].split())))
    # reorder map by number of new words introduced in each sentence (compared to words previously seen)
    map_ordered_by_num_new_words = _order_sentences_by_num_new_words(ordered_map, min_sentence_length, max_card_count)
    return map_ordered_by_num_new_words

def parse_cli():

    parser = argparse.ArgumentParser(description='Spoonfed CommonVoice CLI.')
    parser.add_argument("audio", help="path to audio directory (should end with /)")
    parser.add_argument("tsv", help="path to tsv file")
    parser.add_argument("lang_name", help="language name")
    parser.add_argument("lang_code", help="Two letter code used by Google Translate to identify a language")
    parser.add_argument("length", help="minimum length of sentences to include in deck", type=int)
    parser.add_argument("count", help="max number of cards to include in deck", type=int)
    parser.add_argument("-l", "--listen", help="make a deck for listening practice as well", action="store_true")

    args = parser.parse_args()
    return args

def run():
    args = parse_cli()
    # read the csv into memory
    data_map = build_audio_path_to_sentence_map(args) # key is audio path, value is sentence
    print("CSV INPUT HAS {0} ROWS".format(len(data_map.keys())))

    reading_deck_name = 'CommonVoice::{0}::Reading Notes'.format(args.lang_name)
    # create deck if it doesn't already exist
    existing_decks = invoke('deckNames')
    if reading_deck_name not in existing_decks:
        invoke('createDeck', deck=reading_deck_name)

    audio_paths_ordered = apply_ordering_to_notes(data_map, args.length, args.count)
    copy_files_to_anki_store(audio_paths_ordered.keys(), args)
    print("FILTERED MAP HAS {0} ROWS".format(len(audio_paths_ordered.keys())))
    # always make reading notes
    add_reading_notes_to_anki_connect(reading_deck_name, audio_paths_ordered, data_map, args.lang_code)
    if args.listen:
        listening_deck_name = 'CommonVoice::{0}::Listening Notes'.format(args.lang_name)
        if listening_deck_name not in existing_decks:
            invoke('createDeck', deck=listening_deck_name)
        add_listening_notes_to_anki_connect(listening_deck_name, audio_paths_ordered, data_map, args.lang_code)


if __name__ == "__main__":
    run()
