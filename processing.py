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
from openai import OpenAI
import json
import json5

def run(audio_path):
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

    def reformat_to_json5(string):
        try:
            return json5.loads(string)
        except json5.JSONDecodeError as e:
            print(f"Error decoding JSON: {e}")
            return None

    # print(get_large_audio_transcription_on_silence("MLK_Something_happening.mp3"))

    # TODO: The 'openai.my_api_key' option isn't read in the client API. You will need to pass it when you instantiate the client, e.g. 'OpenAI(my_api_key="")'

    os.environ['OPENAI_API_KEY'] = ''

    client = OpenAI(
    api_key=os.environ['OPENAI_API_KEY'],  # this is also the default, it can be omitted
    )

    # Initialize the system message
    messages = [{"role": "system", "content": "You are an intelligent assistant."}]

    # Assume `get_large_audio_transcription_on_silence` is a function that processes the audio file
    # message = get_large_audio_transcription_on_silence(audio_path)

    message = "Patient stated 'I feel short of breath' when the RN came in to check on them. Vitals signs showed BP 110/75 HR 100 RR 22 SPO2 89. Patient appeared fatigued and pale. May be suffering from asthma. This RN contacted the charge RN, rapid response nurse, and primary care physician. Oxygen was given to the patient via nasal cannula. SPO2 increased to 95, respiratory rate slowed to 18. The patient was transferred off of the med-surg unit and sent to the ICU due to unstable condition. Report given to ICU nurse who will continue to monitor the patient's condition. "

                #    "These categories include subjective (medial history told by patients or their friends), "
                #    "objective (numerical data observed during visit), "
                #    "assessment (medical concern or concerns by nurse), "
                #    "plan (diagnosis and care plan, including any prescriptions, self-care, follow-ups, or referrals if applicable), "
                #    "intervention (what nurse did to the patient if anything, how well the intervention worked, and what changes are needed if any). "

    if message:
        # Update the message with the transcription
        message = ("The text after the ### symbols is an audio transciption of a nurse reading patient notes. "
                #    "Using this text content, create a properly formatted .json file with 5 string variables. "
                    "Parse this text into 5 categories, including: "
                "subjective (medical history, background, and patient words), "
                "objective (measurable and qualitative info), "
                "assessment (predictions about patient health issue), "
                "plan (treatment plan for patient), "
                "intervention (actions taken if any and what happened as a result). "
                #    "Feel free to split the content in sentences into different categories. "
                "All text must be in a category. Content is grouped together and given in the order the categories were given. "
                "Output text using each of these categories as one line. "
                    "Categories should be empty if the text fits other categories better. Only write the text content for each line, do not label each line. "
                    "Any text after the fifth line should be recategorized and placed in the correct line."
                    "Print in this order: subjective, objective, assessment, plan, intervention. Only add text directly coming from the audio transcription. ALL text from audio transcription MUST be in a line. Must make EXACTLY 5 lines of output. Print ALL text uncategorized on the 6th line. ### "
                    # "Do not output any extraneous text other than the .json file text. The output should start with { and end with }.  "
                + message)

        # Append the user message to the conversation history
        messages.append({"role": "user", "content": message})

        # Correct the method call to use the right function
        response = client.chat.completions.create(model="gpt-3.5-turbo",  # Replace with the desired model (can also use "gpt-3.5-turbo")
        messages=messages)

        # Extract the reply from the response
        reply = response.choices[0].message.content
        print(f"ChatGPT: {reply}")

        with open('output.txt', 'w') as file:
            file.write(reply)

        lines = reply.split('\n')

        non_empty_lines = [line for line in lines if line]

        labels = ["subjective", "objective", "assessment", "plan", "intervention", "other"]

        json_object = {}

        for i in range(5):
            json_object[labels[i]] = non_empty_lines[i]

        json_object[labels[5]] = ""

        for i in range(5, len(non_empty_lines)):
            json_object[labels[5]] += non_empty_lines[i]

        if json_object is not None:
        # Save to a JSON file
            with open('output.json', 'w') as json_file:
                json.dump(json_object, json_file, indent=4)  # Use indent for pretty formatting


        # Append the assistant's reply to the conversation history
        messages.append({"role": "assistant", "content": reply})
        return json_object
