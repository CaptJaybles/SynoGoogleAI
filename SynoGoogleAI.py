from flask import Flask, request
import json
import os
import time
import requests
import threading
from synology import OutgoingWebhook
from settings import *
import google.generativeai as genai
import google.generativeai as palm
import queue

app = Flask(__name__)
task_queue = queue.Queue()
processing_semaphore = threading.Semaphore(value=1)

genai.configure(api_key=GOOGLEAI_API_KEY)
genai.ChatSession(model=GEMINI_MODEL, history=None)
gemini_model = genai.GenerativeModel(model_name=GEMINI_MODEL)
gemini_chat = gemini_model.start_chat()

current_topic = False
set_context = CONTEXT
palm_response = None

def send_back_response(output_text, user_id):
    response = output_text
    chunks = []
    current_chunk = ""
    sentences = response.split("\n\n")
    for sentence in sentences:
        if len(current_chunk) + len(sentence) + 2 <= 256:
            current_chunk += sentence + "\n\n"
        else:
            chunks.append(current_chunk.strip())
            current_chunk = sentence + "\n\n"
    if current_chunk:
        chunks.append(current_chunk.strip())
    for chunk in chunks:
        payload = 'payload=' + json.dumps({
            'text': chunk,
            "user_ids": [int(user_id)]
        })
        try:
            response = requests.post(INCOMING_WEBHOOK_URL, payload)
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            return "Error", 500
        finally:
            pass
    return processing_semaphore.release()

def generate_model_response(input_text, user_id):

    if MODEL == "GEMINI":
        safety_settings_gemini = [
          {
            "category": "HARM_CATEGORY_HARASSMENT",
            "threshold": "BLOCK_NONE"
          },
          {
            "category": "HARM_CATEGORY_HATE_SPEECH",
            "threshold": "BLOCK_NONE"
          },
          {
            "category": "HARM_CATEGORY_SEXUALLY_EXPLICIT",
            "threshold": "BLOCK_NONE"
          },
          {
            "category": "HARM_CATEGORY_DANGEROUS_CONTENT",
            "threshold": "BLOCK_NONE"
         },
        ]
        generation_config = {
            'temperature': TEMPURATURE,
            'candidate_count': 1,
            'top_k': TOP_K,
            'top_p': TOP_P,
            'max_output_tokens': MAX_TOKENS,
            'stop_sequences': STOP_SEQUENCES
        }

        def generate_response(input_text, user_id):
            global gemini_chat, gemini_model, gemini_chat_session
            if input_text.startswith("/reset"):
                genai.ChatSession(model=GEMINI_MODEL, history=None)
                gemini_model = genai.GenerativeModel(model_name=GEMINI_MODEL)
                gemini_chat = gemini_model.start_chat()
                output = "conversation Reset"
                send_back_response(output, user_id)

            elif input_text.startswith("/rewind"):
                gemini_chat.rewind()
                output = "Conversation Rewound"
                send_back_response(output, user_id)

            elif input_text.startswith("/model"):
                global MODEL
                input = input_text.replace("/model", "").strip()
                if input.lower() == "palm":
                    MODEL = "PALM"
                    output = f"Model is now set to Palm"
                elif input.lower() == "gemini":
                    MODEL = "GEMINI"
                    output = f"Model is now set to Gemini"
                else:
                    MODEL = None
                    output = f"The model name was misspelled please try again /model gemini|palm"
                send_back_response(output, user_id)

            else:
                def generate_message(input_text, user_id):
                    global gemini_chat
                    gemini_response = gemini_chat.send_message(content=input_text, generation_config=generation_config, safety_settings=safety_settings_gemini)
                    output = gemini_response.text
                    send_back_response(output, user_id)
                threading.Thread(target=generate_message, args=(input_text, user_id)).start()

    elif MODEL == "PALM":
        safety_settings_palm = [
          {
            "category": "HARM_CATEGORY_UNSPECIFIED",
            "threshold": "BLOCK_NONE"
          },
          {
            "category": "HARM_CATEGORY_DEROGATORY",
            "threshold": "BLOCK_NONE"
          },
          {
            "category": "HARM_CATEGORY_TOXICITY",
            "threshold": "BLOCK_NONE"
          },
          {
            "category": "HARM_CATEGORY_VIOLENCE",
            "threshold": "BLOCK_NONE"
         },
          {
            "category": "HARM_CATEGORY_SEXUAL",
            "threshold": "BLOCK_NONE"
          },
          {
            "category": "HARM_CATEGORY_MEDICAL",
            "threshold": "BLOCK_NONE"
          },
          {
            "category": "HARM_CATEGORY_DANGEROUS",
            "threshold": "BLOCK_NONE"
         },
        ]
        defaults = {
            'model': PALM_MODEL,
            'temperature': TEMPURATURE,
            'candidate_count': 1,
            'top_k': TOP_K,
            'top_p': TOP_P,
        }

        def generate_response(input_text, user_id):
            global set_context, current_topic, palm_response
            if input_text.startswith("/reset"):
                current_topic = False
                set_context = CONTEXT
                palm_response = None
                output = "conversation Reset"
                send_back_response(output, user_id)

            elif input_text.startswith("/model"):
                global MODEL
                input = input_text.replace("/model", "").strip()
                if input.lower() == "palm":
                    MODEL = "PALM"
                    output = f"Model is now set to Palm"
                elif input.lower() == "gemini":
                    MODEL = "GEMINI"
                    output = f"Model is now set to Gemini"
                else:
                    MODEL = None
                    output = f"The model name was misspelled please try again /model gemini|palm"
                send_back_response(output, user_id)

            elif input_text.startswith("/context"):
                set_context = input_text.replace("/context", "").strip().capitalize()
                output = f"Temp Context Set"
                send_back_response(output, user_id)

            elif input_text.startswith("/override"):
                def generate_override_message(input_text, user_id):
                    input_prompt = input_text.replace("/override", "").strip()
                    palm_output = genai.generate_text(**defaults, prompt=input_prompt, max_output_tokens=MAX_TOKENS, safety_settings=safety_settings_palm, stop_sequences=STOP_SEQUENCES)
                    answer = palm_output.result
                    send_back_response(answer, user_id)
                threading.Thread(target=generate_override_message, args=(input_text, user_id)).start()

            # Normal chat prompt
            else:
                def generate_message(input_text, user_id):
                    global current_topic, palm_response
                    if current_topic == True:
                        palm_response = palm_response.reply(input_text)
                        output = palm_response.last
                        if output == None:
                            safety_output = f"Google safety filter kicked in try /override 'message' to get the answer"
                            send_back_response(safety_output, user_id)
                        else:
                            current_topic = True
                            send_back_response(output, user_id)
                    else:
                        init_message = []
                        init_message.append(input_text)
                        init_message = init_message[-1:]
                        palm_response = genai.chat(**defaults, context=f'{set_context}', examples=EXAMPLES, messages=init_message)
                        output = palm_response.last
                        if output == None:
                            safety_output = f"Google safety filter kicked in try /override 'message' to get the answer"
                            send_back_response(safety_output, user_id)
                        else:
                            current_topic = True
                            send_back_response(output, user_id)
                threading.Thread(target=generate_message, args=(input_text, user_id)).start()
    else:
        def generate_response(input_text, user_id):
            global MODEL
            if input_text.startswith("/model"):
                input = input_text.replace("/model", "").strip()
                if input.lower() == "palm":
                    MODEL = "PALM"
                    output = f"Model is now set to Palm"
                elif input.lower() == "gemini":
                    MODEL = "GEMINI"
                    output = f"Model is now set to Gemini"
                else:
                    MODEL = None
                    output = f"The model name was misspelled please try again /model gemini|palm"
                send_back_response(output, user_id)
            else:
                output = f"Model type is not set please try again /model gemini|palm"
                send_back_response(output, user_id)
    threading.Thread(target=generate_response, args=(input_text, user_id)).start()
    return "..."

@app.route('/SynoGoogleAI', methods=['POST'])
def chatbot():
    token = SYNOCHAT_TOKEN
    webhook = OutgoingWebhook(request.form, token)
    if not webhook.authenticate(token):
        return webhook.createResponse('Outgoing Webhook authentication failed: Token mismatch.')
    input_text = webhook.text
    user_id = webhook.user_id
    task_queue.put((input_text, user_id))
    return "Task queued for processing"

def process_tasks():
    while True:
        processing_semaphore.acquire()
        try:
            input_text, user_id = task_queue.get()
            generate_model_response(input_text, user_id)
        finally:
            task_queue.task_done()

processing_thread = threading.Thread(target=process_tasks, daemon=True)
processing_thread.start()

if __name__ == '__main__':
    app.run('0.0.0.0', port=FLASK_PORT, debug=False, threaded=True)