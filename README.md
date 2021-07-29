# Spoonfed<Language>
## What is this?

I have commonvoice data - brief mp3 sentences and their transcription.
I want to generate `Spoonfed<Language>`

## Remaining Goals (in no particular order)
1. Parse correctly and pinyin for chinese
1. A new word is not another conjugation of the same word
1. Use google cloud translate api to make cards of english -> language
1. Api to handle and process compressed file
1. Read deck state from AnkiConnect to highlight/prioritize unknown words
1. Web app


### Completed goals
1. Generate anki cards - play the audio on one side, then check audio recognition.
1. Add button hyperlink to google translate for sentence
1. Sync to Anki with AnkiConnect
1. Ordering such that each sentence introduces exactly 1 new word
1. Make separate decks for reading and listening(with cloze deletions)
1. Build in cloze deletions
1. Make comparisons lowercase and stripped (but not output text)
1. Make package (so people can just pip install)
