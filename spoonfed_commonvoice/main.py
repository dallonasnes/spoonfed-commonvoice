import csv
import json
import os
import os.path
from shutil import copyfile
from typing import List
import urllib.request
import urllib.parse
from collections import OrderedDict
import sys
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

def build_audio_path_to_sentence_map():
    map = {}
    with open(VALIDATED_TSV_PATH) as csv_file:
        csv_reader = csv.reader(csv_file, delimiter='\t')
        line_count = 0
        for row in csv_reader:
            if line_count == 0:
                # ignore header row
                line_count += 1
            else:
                audio_path = row[1]
                sentence = row[2]
                map[audio_path] = sentence
    return map

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
    map = {}
    for sentence in sentences:
        for word in sentence.split():
            word = word.strip().lower()
            if word in map:
                map[word] += 1
            else:
                map[word] = 1
    return map


def add_listening_notes_to_anki_connect(deck_name, audio_paths_ordered, map, lang_code):
    # note that if the note already exists, it won't be modified
    all_notes = []
    word_frequency_map = _build_word_frequency_map(list(audio_paths_ordered.values()))
    print("BEGINNING TO GENERATE LISTENING NOTES FROM SENTENCES")
    for audio_path in tqdm(audio_paths_ordered):
        sentence = map[audio_path]
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

def add_reading_notes_to_anki_connect(deck_name, audio_paths_ordered, map, lang_code):
    # note that if the note already exists, it won't be modified
    all_notes = []
    print("BEGINNING TO GENERATE READING NOTES FROM SENTENCES")
    for audio_path in tqdm(audio_paths_ordered):
        sentence = map[audio_path]
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

def copy_files_to_anki_store(relative_audio_paths: List):
    """
        For each audio file,
        first check if file exists in Anki store,
        if not then copy from local to there
    """
    print("COPYING FILES TO ANKI MEDIA STORE")
    for audio_name in tqdm(relative_audio_paths):
        dest_path = ANKI_MEDIA_PATH + audio_name
        if not os.path.isfile(dest_path):
            src_path = AUDIO_DIR_PATH + audio_name
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

def _remove_dup_sentences(ordered_map):
    """Remove any sentences that don't introduce new words"""
    deduped_ordered_map = OrderedDict()
    previously_seen_words = set()
    for key, sentence in ordered_map.items():
        has_unseen_words = False
        for word in sentence.split():
            word = word.strip().lower()
            if word not in previously_seen_words:
                has_unseen_words = True
                previously_seen_words.add(word)
        if has_unseen_words:
            deduped_ordered_map[key] = sentence
    return deduped_ordered_map

def _order_sentences_by_min_num_new_words(sentences):
    sentences_ordered_by_num_new_words = []
    unused_sentences = sentences.copy()
    if MIN_SENTENCE_LENGTH > 1:
        unused_sentences = list(filter(lambda x: len(x.split()) >= MIN_SENTENCE_LENGTH, unused_sentences))
    previously_seen_words = set()
    print("BEGINNING TO APPLY ORDERING TO {0} SENTENCES".format(len(unused_sentences)))
    with tqdm(total=len(unused_sentences)) as pbar:
        while len(unused_sentences) > 0:
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
                if new_word_count < 2:
                    # we found a sentence with zero or one new word, so we can add it right away
                    idx = unused_sentences.index(sentence)
                    sentence = unused_sentences.pop(idx)
                    sentences_ordered_by_num_new_words.append(sentence)
                    for word in sentence.split():
                        word = word.strip().lower()
                        previously_seen_words.add(word)
                    already_popped_sentence = True
                    pbar.update(1)
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
                already_popped_sentence = True
                for word in sentence.split():
                    word = word.strip().lower()
                    previously_seen_words.add(word)
                pbar.update(1)
    
    print("FINISHED APPLYING ORDERING TO SENTENCES")
    return sentences_ordered_by_num_new_words        

def _build_map_audio_to_sentence_ordered_by_min_new_words_in_sentence(sentences_ordered_by_min_num_new_words, sentence_to_audio_map):
    rtn_val = OrderedDict()
    for sentence in sentences_ordered_by_min_num_new_words:
        audio_path = sentence_to_audio_map[sentence]
        rtn_val[audio_path] = sentence
    return rtn_val

def _order_sentences_by_num_new_words(deduped_ordered_map):
    sentence_to_audio_map = _invert_ordered_dict(deduped_ordered_map)
    sentences_ordered_by_min_num_new_words = _order_sentences_by_min_num_new_words(list(sentence_to_audio_map.keys()))
    map_audio_to_sentence_ordered_by_min_new_words_in_sentence = _build_map_audio_to_sentence_ordered_by_min_new_words_in_sentence(sentences_ordered_by_min_num_new_words, sentence_to_audio_map)
    return map_audio_to_sentence_ordered_by_min_new_words_in_sentence

def apply_ordering_to_notes(map):
    # order map by length of each sentence
    ordered_map = OrderedDict(sorted(map.items(), key=lambda t: len(t[1].split())))
    # reorder map by number of new words introduced in each sentence (compared to words previously seen)
    map_ordered_by_num_new_words = _order_sentences_by_num_new_words(ordered_map)
    # remove all sentences that intro 0 new words
    deduped_ordered_audio_to_sentence_map = _remove_dup_sentences(map_ordered_by_num_new_words)
    return deduped_ordered_audio_to_sentence_map

def parse_cli():
    global AUDIO_DIR_PATH
    global VALIDATED_TSV_PATH
    global LANGUAGE_NAME
    global LANG_CODE
    global MIN_SENTENCE_LENGTH
    global MAKE_READING_NOTES
    global MAKE_LISTENING_NOTES
    AUDIO_DIR_PATH = input("What is path to audio directory? (end with a /)\n").strip()
    VALIDATED_TSV_PATH = input("What is path to validated tsv file?\n").strip()
    LANGUAGE_NAME = input("What is language name?\n").strip().lower()
    LANG_CODE = input("What is language code?\n").strip().lower()
    MIN_SENTENCE_LENGTH = int(input("What is the smallest sentence size to allow?\n").strip())
    MAKE_READING_NOTES = input("Do you want reading notes? (y/n)\n").strip().lower()[0] == "y"
    MAKE_LISTENING_NOTES = input("Do you want listening notes? (y/n)\n").strip().lower()[0] == "y"
    if MAKE_READING_NOTES is False and MAKE_LISTENING_NOTES is False:
        print("You don't want any Anki notes made. Exiting.")
        sys.exit(0)

def run():
    parse_cli()
    # read the csv into memory
    map = build_audio_path_to_sentence_map() # key is audio path, value is sentence
    print("CSV INPUT HAS {0} ROWS".format(len(map.keys())))

    lang_code = LANG_CODE
    reading_deck_name = 'CommonVoice::{0} Reading Notes'.format(LANGUAGE_NAME)
    listening_deck_name = 'CommonVoice::{0} Listening Notes'.format(LANGUAGE_NAME)
    # create deck if it doesn't already exist
    existing_decks = invoke('deckNames')
    if reading_deck_name not in existing_decks:
        invoke('createDeck', deck=reading_deck_name)
    if listening_deck_name not in existing_decks:
        invoke('createDeck', deck=listening_deck_name)

    audio_paths_ordered = apply_ordering_to_notes(map)
    copy_files_to_anki_store(audio_paths_ordered.keys())
    print("FILTERED MAP HAS {0} ROWS".format(len(audio_paths_ordered.keys())))
    if MAKE_READING_NOTES:
        add_reading_notes_to_anki_connect(reading_deck_name, audio_paths_ordered, map, lang_code)
    if MAKE_LISTENING_NOTES:
        add_listening_notes_to_anki_connect(listening_deck_name, audio_paths_ordered, map, lang_code)


if __name__ == "__main__":
    run()
