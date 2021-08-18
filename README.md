# Spoonfed CommonVoice

Command line interface useful for foreign language learning that generates flash cards to practice reading and listening comprehension from [Mozilla's CommonVoice](https://commonvoice.mozilla.org/en/datasets) multi-language voice dataset and creates notes that sync with [Anki](https://apps.ankiweb.net/).

While some apps already feature flash cards that have extensive audio and transcription data, their data doesn't include many languages and their process of curating datasets is expensive. CommonVoice has more data in more languages and will continue to grow.

## How to use these cards
Each card pairs speech audio with the transcript of what was said (validated by the contributors to the CommonVoice project).

Improve listening comprehension by reading the transcription only after listening to the audio and filling in the [cloze deletion](https://www.ollielovell.com/edtech/anki3/) card.


Improve pronunciation by reading a sentence out loud and then listen to speech.

## Features

- Syncs to Anki with AnkiConnect
- Cards are ordered such that only one new word is introduced at a time
- Separate deck for listening practice includes cloze deletions

## How to Use pip package (main is not a release branch)

1. Run `pip install spoonfed-commonvoice`
1. Download and unzip CommonVoice file
1. Setup [Anki Connect Plugin](https://ankiweb.net/shared/info/2055492159) on Desktop Anki installation
1. Create CommonVoice reading and listening decks in Anki
    - `CommonVoice note` with fields `Sentence, Audio, Translate Link`
    - `CommonVoice cloze note` with fields `Audio, Sentence, Translate Link`


1. Leave Anki open (so that AnkiConnect server is running)
1. Run `cva` and answer config questions in prompt
