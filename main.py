import csv
import json
import os.path
from shutil import copyfile
from typing import List
import urllib.request
import urllib.parse

"""
External setup:
0. Download and unzip CommonVoice file
1. setup anki connect plugin on desktop anki installation
2. create CommonVoice note deck type
3. Leave Anki open (so that AnkiConnect server is running)
"""

DIR_PATH = "persian-commonvoice/fa/"
CLIPS_SUBPATH = "clips/"
INPUT_TSV = "validated.tsv"
ANKI_MEDIA_PATH = "/Users/dev/Library/Application Support/Anki2/User 1/collection.media/"
LANGUAGE_NAME = "persian"
LANG_CODE = "fa"

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
    with open(DIR_PATH + INPUT_TSV) as csv_file:
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

def add_notes_to_anki_connect(deck_name, audio_paths_ordered, map, lang_code):
    # note that if the note already exists, it won't be modified
    all_notes = []
    for audio_path in audio_paths_ordered:
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
  
    invoke('addNotes', notes=all_notes)

def copy_files_to_anki_store(relative_audio_paths: List):
    """
        For each audio file,
        first check if file exists in Anki store,
        if not then copy from local to there
    """
    for audio_name in relative_audio_paths:
        dest_path = ANKI_MEDIA_PATH + audio_name
        if not os.path.isfile(dest_path):
            src_path = DIR_PATH + CLIPS_SUBPATH + audio_name
            copyfile(src_path, dest_path)

def _get_word_frequency_map(sentences):
    vocab_freq_map = {}
    for sentence in sentences:
        for word in sentence.split():
            if word in vocab_freq_map:
                vocab_freq_map[word] += 1
            else:
                vocab_freq_map[word] = 1
    return vocab_freq_map


def apply_ordering_to_notes(map):
    vocab_freq_map = _get_word_frequency_map(map.values())
    # now want to score each sentence by audio path

    return []

def main():
    # read the csv into memory
    map = build_audio_path_to_sentence_map() # key is audio path, value is sentence

    lang_code = LANG_CODE
    deck_name = 'CommonVoice::{0} Notes'.format(LANGUAGE_NAME)
    # create deck if it doesn't already exist
    existing_decks = invoke('deckNames')
    if deck_name not in existing_decks:
        invoke('createDeck', deck=deck_name)

    audio_paths_ordered = apply_ordering_to_notes(map)
    copy_files_to_anki_store(map.keys())
    add_notes_to_anki_connect(deck_name, audio_paths_ordered, map, lang_code)


if __name__ == "__main__":
    # TODO: read in dir path, lang name and lang code from CLI
    main()
