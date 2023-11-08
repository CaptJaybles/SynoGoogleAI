from flask import Flask, request
import json
import os
import time
import requests
import threading
from synology import OutgoingWebhook
from settings import *
import google.generativeai as palm
import queue

app = Flask(__name__)
palm.configure(api_key=PALM_API_KEY)
safety_settings = [
    palm.types.SafetySettingDict(category=0, threshold=4),
    palm.types.SafetySettingDict(category=1, threshold=4),
    palm.types.SafetySettingDict(category=2, threshold=4),
    palm.types.SafetySettingDict(category=3, threshold=4),
    palm.types.SafetySettingDict(category=4, threshold=4),
    palm.types.SafetySettingDict(category=5, threshold=4),
    palm.types.SafetySettingDict(category=6, threshold=4),
]
current_topic = False
set_context = CONTEXT
response = None
messages = []

task_queue = queue.Queue()
processing_semaphore = threading.Semaphore(value=1)

defaults = {
    'model': MODEL,
    'temperature': TEMPURATURE,
    'candidate_count': 1,
    'top_k': TOP_K,
    'top_p': TOP_P,
}

def send_back_message(user_id, output_text):
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
            processing_semaphore.release()
    return "success"

def reset_conversation():
    global current_topic, set_context, messages
    current_topic = False
    set_context = CONTEXT
    messages = []

def generate_message(input_text, user_id):
    global current_topic, response, messages, set_context
    if current_topic == True:
        messages.append(input_text)
        messages = messages[-1:]
        answer = response.reply(input_text)
        output = answer.last
        if output == None:
            safety_output = f"Google safety filter kicked in try /override 'message' to get the answer"
            send_back_message(user_id, safety_output)
        else:
            current_topic = True
            send_back_message(user_id, output)
    else:
        messages.append(input_text)
        messages = messages[-1:]
        response = palm.chat(**defaults, context=f'{set_context}', examples=EXAMPLES, messages=messages)
        output = response.last
        if output == None:
            safety_output = f"Google safety filter kicked in try /override 'message' to get the answer"
            send_back_message(user_id, safety_output)
        else:
            current_topic = True
            send_back_message(user_id, output)

def generate_override_message(input_text, user_id):
    input_prompt = input_text.replace("/override", "").strip()
    output = palm.generate_text(prompt=input_prompt, max_output_tokens=MAX_TOKENS, safety_settings=safety_settings, temperature=TEMPURATURE, top_p=TOP_P, top_k=TOP_K)
    answer = output.result
    send_back_message(user_id, answer)

def generate_response(input_text, user_id):
    # Resets model conversation
    if input_text.startswith("/reset"):
        reset_conversation()
        output = "conversation Reset"
        return send_back_message(user_id, output)

    # Custom prompt without messing up context and conversation
    elif input_text.startswith("/override"):
        threading.Thread(target=generate_override_message, args=(input_text, user_id)).start()
        return "..."

    # Set temporary context
    elif input_text.startswith("/context"):
        global set_context
        set_context = input_text.replace("/context", "").strip().capitalize()
        output = f"Temp Context Set"
        return send_back_message(user_id, output)

    # Normal chat prompt
    else:
        global current_topic
        threading.Thread(target=generate_message, args=(input_text, user_id)).start()
        return "..."
    
@app.route('/SynologyLLM', methods=['POST'])
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
            generate_response(input_text, user_id)
        finally:
            task_queue.task_done()

processing_thread = threading.Thread(target=process_tasks, daemon=True)
processing_thread.start()

if __name__ == '__main__':
    app.run('0.0.0.0', port=FLASK_PORT, debug=False, threaded=True)