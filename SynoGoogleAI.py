from flask import Flask, request
import json
import os
import time
import requests
import threading
from synology import OutgoingWebhook
from settings import *
import google.generativeai as genai
import queue

app = Flask(__name__)
task_queue = queue.Queue()
processing_semaphore = threading.Semaphore(value=1)

genai.configure(api_key=GOOGLEAI_API_KEY)
gemini_model = genai.GenerativeModel(model_name=GEMINI_MODEL)
gemini_user_data = {}
palm_user_data = {}

def send_back_response(output_text, user_id):
    chunks = []
    current_chunk = ""
    sentences = output_text.split("\n\n")
    for sentence in sentences:
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
    return processing_semaphore.release()

def generate_model_response(input_text, user_id, user_context):
    global gemini_user_data, palm_user_data

    gemini_chat = gemini_user_data[user_id]['gemini_chat']
    set_context = palm_user_data[user_id]['set_context']
    current_topic = palm_user_data[user_id]['current_topic']
    palm_response = palm_user_data[user_id]['palm_response']

    MODEL = user_context.get('model', '')

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
            global gemini_user_data, palm_user_data
            gemini_chat = user_context.get('gemini_chat', '')

            if input_text.startswith("/reset"):
                gemini_user_data[user_id] = {
                    'gemini_chat': gemini_model.start_chat(history=[]),
                    'model': MODEL
                }
                output = "conversation Reset"
                send_back_response(output, user_id)

            elif input_text.startswith("/rewind"):
                gemini_rewind = gemini_chat.rewind()
                gemini_user_data[user_id] = {
                    'gemini_chat': gemini_chat,
                    'model': MODEL
                }
                output = "Conversation Rewound"
                send_back_response(output, user_id)

            elif input_text.startswith("/model"):
                input = input_text.replace("/model", "").strip()
                if input.lower() == "palm":
                    gemini_user_data[user_id] = {'gemini_chat': gemini_chat, 'model': 'PALM'}
                    palm_user_data[user_id] = {
                        'current_topic': current_topic,
                        'set_context': set_context,
                        'palm_response': palm_response,
                        'model': 'PALM'
                    }
                    output = f"Model is now set to Palm"
                elif input.lower() == "gemini":
                    gemini_user_data[user_id] = {'gemini_chat': gemini_chat, 'model': 'GEMINI'}
                    palm_user_data[user_id] = {
                        'current_topic': current_topic,
                        'set_context': set_context,
                        'palm_response': palm_response,
                        'model': 'GEMINI'
                    }
                    output = f"Model is now set to Gemini"
                else:
                    gemini_user_data[user_id] = {'gemini_chat': gemini_chat, 'model': None}
                    palm_user_data[user_id] = {
                        'current_topic': current_topic,
                        'set_context': set_context,
                        'palm_response': palm_response,
                        'model': None
                    }
                    output = f"The model name was misspelled please try again /model gemini|palm"
                send_back_response(output, user_id)

            else:
                def generate_message(input_text, user_id):
                    global gemini_user_data
                    gemini_response = gemini_chat.send_message(content=input_text, generation_config=generation_config, safety_settings=safety_settings_gemini)
                    output = gemini_response.text
                    gemini_user_data[user_id] = {
                        'gemini_chat': gemini_chat,
                        'model': MODEL
                    }
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

        def generate_response(input_text, user_id):
            global gemini_user_data, palm_user_data
            current_topic = user_context.get('current_topic', '')
            current_context = user_context.get('set_context', '')
            palm_response = user_context.get('palm_response', '')

            if input_text.startswith("/reset"):
                palm_user_data[user_id] = {
                    'current_topic': False,
                    'set_context': CONTEXT,
                    'palm_response': None,
                    'model': MODEL
                }
                output = "conversation Reset"
                send_back_response(output, user_id)

            elif input_text.startswith("/model"):
                input = input_text.replace("/model", "").strip()
                if input.lower() == "palm":
                    gemini_user_data[user_id] = {
                        'gemini_chat': gemini_chat,
                        'model': 'PALM'
                    }
                    palm_user_data[user_id] = {
                        'current_topic': current_topic,
                        'set_context': current_context,
                        'palm_response': palm_response,
                        'model': 'PALM'
                    }
                    output = f"Model is now set to Palm"
                elif input.lower() == "gemini":
                    gemini_user_data[user_id] = {
                        'gemini_chat': gemini_chat,
                        'model': 'GEMINI'
                    }
                    palm_user_data[user_id] = {
                        'current_topic': current_topic,
                        'set_context': current_context,
                        'palm_response': palm_response,
                        'model': 'GEMINI'
                    }
                    output = f"Model is now set to Gemini"
                else:
                    gemini_user_data[user_id] = {
                        'gemini_chat': gemini_chat,
                        'model': None
                    }
                    palm_user_data[user_id] = {
                        'current_topic': current_topic,
                        'set_context': current_context,
                        'palm_response': palm_response,
                        'model': None
                    }
                    output = f"The model name was misspelled please try again /model gemini|palm"
                send_back_response(output, user_id)

            elif input_text.startswith("/context"):
                new_context = input_text.replace("/context", "").strip().capitalize()
                palm_user_data[user_id] = {
                    'current_topic': current_topic,
                    'set_context': new_context,
                    'palm_response': palm_response,
                    'model': MODEL
                }
                output = f"Temp Context Set"
                send_back_response(output, user_id)

            elif input_text.startswith("/override"):
                def generate_override_message(input_text, user_id):
                    input_prompt = input_text.replace("/override", "").strip()
                    palm_output = genai.generate_text(prompt=input_prompt, model=PALM_TEXT_MODEL, temperature=TEMPURATURE, candidate_count=1, top_k=TOP_K, top_p=TOP_P, max_output_tokens=MAX_TOKENS, safety_settings=safety_settings_palm, stop_sequences=STOP_SEQUENCES)
                    answer = palm_output.result
                    send_back_response(answer, user_id)
                threading.Thread(target=generate_override_message, args=(input_text, user_id)).start()

            # Normal chat prompt
            else:
                def generate_message(input_text, user_id):
                    global palm_user_data
                    palm_response = user_context.get('palm_response', '')
                    if current_topic == True:
                        response = palm_response.reply(input_text)
                        output = response.last
                        palm_user_data[user_id] = {
                            'current_topic': current_topic,
                            'set_context': current_context,
                            'palm_response': response,
                            'model': MODEL
                        }
                        if output == None:
                            safety_output = f"Google safety filter kicked in try /override 'message' to get the answer"
                            send_back_response(safety_output, user_id)
                        else:
                            palm_user_data[user_id] = {
                                'current_topic': True,
                                'set_context': current_context,
                                'palm_response': response,
                                'model': MODEL
                            }
                            send_back_response(output, user_id)
                    else:
                        defaults = {'model': PALM_CHAT_MODEL, 'temperature': TEMPURATURE, 'candidate_count': 1, 'top_k': TOP_K, 'top_p': TOP_P, 'context': current_context, 'examples': EXAMPLES}
                        init_message = []
                        init_message.append(input_text)
                        init_message = init_message[-1:]
                        palm_response = genai.chat(**defaults, messages=init_message)
                        output = palm_response.last
                        palm_user_data[user_id] = {
                            'current_topic': current_topic,
                            'set_context': current_context,
                            'palm_response': palm_response,
                            'model': MODEL
                        }
                        if output == None:
                            safety_output = f"Google safety filter kicked in try /override 'message' to get the answer"
                            send_back_response(safety_output, user_id)
                        else:
                            palm_user_data[user_id] = {
                                'current_topic': True,
                                'set_context': current_context,
                                'palm_response': palm_response,
                                'model': MODEL
                            }
                            send_back_response(output, user_id)
                threading.Thread(target=generate_message, args=(input_text, user_id)).start()
    else:
        def generate_response(input_text, user_id):
            global gemini_user_data, palm_user_data
            if input.lower() == "palm":
                gemini_user_data[user_id] = {
                    'gemini_chat': gemini_chat,
                    'model': 'PALM'
                }
                palm_user_data[user_id] = {
                    'current_topic': current_topic,
                    'set_context': set_context,
                    'palm_response': palm_response,
                    'model': 'PALM'
                }
                output = f"Model is now set to Palm"
            elif input.lower() == "gemini":
                gemini_user_data[user_id] = {
                    'gemini_chat': gemini_chat,
                    'model': 'GEMINI'
                }
                palm_user_data[user_id] = {
                    'current_topic': current_topic,
                    'set_context': set_context,
                    'palm_response': palm_response,
                    'model': 'GEMINI'
                }
                output = f"Model is now set to Gemini"
            else:
                gemini_user_data[user_id] = {
                    'gemini_chat': gemini_chat,
                    'model': None
                }
                palm_user_data[user_id] = {
                    'current_topic': current_topic,
                    'set_context': set_context,
                    'palm_response': palm_response,
                    'model': None
                }
                output = f"The model name was misspelled please try again /model gemini|palm"
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
    if user_id not in gemini_user_data:
        gemini_user_data[user_id] = {
            'gemini_chat': gemini_model.start_chat(history=[]),
            'model': MODEL
        }
    if user_id not in palm_user_data:
        palm_user_data[user_id] = {
            'current_topic': False,
            'set_context': CONTEXT,
            'palm_response': None,
            'model': MODEL
        }
    if gemini_user_data[user_id]['model'] and palm_user_data[user_id]['model'] == 'GEMINI':
        task_queue.put((input_text, user_id, gemini_user_data[user_id]))
    if gemini_user_data[user_id]['model'] and palm_user_data[user_id]['model'] == 'PALM':
        task_queue.put((input_text, user_id, palm_user_data[user_id]))
    return "Task queued for processing"

def process_tasks():
    while True:
        processing_semaphore.acquire()
        try:
            input_text, user_id, user_context = task_queue.get()
            generate_model_response(input_text, user_id, user_context)
        finally:
            task_queue.task_done()

processing_thread = threading.Thread(target=process_tasks, daemon=True)
processing_thread.start()

if __name__ == '__main__':
    app.run('0.0.0.0', port=FLASK_PORT, debug=False, threaded=True)
