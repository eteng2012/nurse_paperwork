# import speech_recognition as sr

# filename = "16-122828-0002.wav"

# r = sr.Recognizer()

# # open the file
# with sr.AudioFile(filename) as source:
#     # listen for the data (load audio to memory)
#     audio_data = r.record(source)
#     # recognize (convert from speech to text)
#     text = r.recognize_google(audio_data)
#     print(text)



# importing libraries 
import speech_recognition as sr 
import os 
from pydub import AudioSegment
from pydub.silence import split_on_silence
import openai

# create a speech recognition object
r = sr.Recognizer()

# a function to recognize speech in the audio file
# so that we don't repeat ourselves in in other functions
def transcribe_audio(path):
    # use the audio file as the audio source
    with sr.AudioFile(path) as source:
        audio_listened = r.record(source)
        # try converting it to text
        text = r.recognize_google(audio_listened)
    return text

# a function that splits the audio file into chunks on silence
# and applies speech recognition
def get_large_audio_transcription_on_silence(path):
    """Splitting the large audio file into chunks
    and apply speech recognition on each of these chunks"""
    # open the audio file using pydub
    sound = AudioSegment.from_file(path)  
    # split audio sound where silence is 500 miliseconds or more and get chunks
    chunks = split_on_silence(sound,
        # experiment with this value for your target audio file
        min_silence_len = 500,
        # adjust this per requirement
        silence_thresh = sound.dBFS-14,
        # keep the silence for 1 second, adjustable as well
        keep_silence=500,
    )
    folder_name = "audio-chunks"
    # create a directory to store the audio chunks
    if not os.path.isdir(folder_name):
        os.mkdir(folder_name)
    whole_text = ""
    # process each chunk 
    for i, audio_chunk in enumerate(chunks, start=1):
        # export audio chunk and save it in
        # the `folder_name` directory.
        chunk_filename = os.path.join(folder_name, f"chunk{i}.wav")
        audio_chunk.export(chunk_filename, format="wav")
        # recognize the chunk
        try:
            text = transcribe_audio(chunk_filename)
        except sr.UnknownValueError as e:
            print("Error:", str(e))
        else:
            text = f"{text.capitalize()}. "
            # print(chunk_filename, ":", text)
            whole_text += text
    # return the text for all chunks detected
    return whole_text

# print(get_large_audio_transcription_on_silence("MLK_Something_happening.mp3"))

# Initialize the system message
# messages = [{"role": "system", "content": "You are an intelligent assistant."}]

# # Assume `get_large_audio_transcription_on_silence` is a function that processes the audio file
# message = get_large_audio_transcription_on_silence("MLK_Something_happening.mp3")

# if message:
#     # Update the message with the transcription
#     message = ("The following text after the : symbol is an audio transcription "
#                "of an MLK speech. Using this text content, create a properly formatted "
#                ".json file with one variable (countries) holding the list of all the countries mentioned in the text: "
#                + message)
    
#     # Append the user message to the conversation history
#     messages.append({"role": "user", "content": message})
    
#     # Correct the method call to use the right function
#     response = openai.ChatCompletion.create(
#         model="gpt-4",  # Replace with the desired model (can also use "gpt-3.5-turbo")
#         messages=messages
#     )

#     # Extract the reply from the response
#     reply = response.choices[0]['message']['content']
#     print(f"ChatGPT: {reply}")
    
#     # Append the assistant's reply to the conversation history
#     messages.append({"role": "assistant", "content": reply})