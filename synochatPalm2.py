from flask import Flask, request
import json
import os
import time
import requests
import threading
from synology import OutgoingWebhook
from settings import *
import google.generativeai as palm

app = Flask(__name__)
palm.configure(api_key=PALM_API_KEY)
current_topic=None
set_context=CONTEXT
response=None
messages = []

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
    return "success"

def reset_conversation():
    global current_topic, set_context, messages 
    current_topic=None
    set_context=CONTEXT
    messages=[]

def generate_response(input_text, user_id):

    #resets model conversation
    if input_text.startswith("/reset"):
        reset_conversation()
        output = "conversation Reset"
        return send_back_message(user_id, output)

    #custom prompt without messing up context and conversation
    elif input_text.startswith("/override"): 
        def generate_message(): 
            input = input_text.replace("/override", "").strip()
            output = palm.generate_text(prompt=f'{input}', safety_settings=None, temperature=TEMPURATURE, top_p=TOP_P, top_k=TOP_K)
            answer = output.result
            send_back_message(user_id, answer)
        threading.Thread(target=generate_message).start()
        return "..."

    #set temporary context
    elif input_text.startswith("/context"):
        global set_context
        set_context = input_text.replace("/context", "").strip().capitalize()
        output = f"Context Set"
        return send_back_message(user_id, output)

    #normal chat prompt
    else:
        global current_topic
        if current_topic:
            def generate_message():
                global response, current_topic, messages
                prompt = f'{input_text}'
                messages.append(f"{input_text}")
                output = response.reply(prompt)
                answer = output.last
                current_topic = f"{answer}"
                send_back_message(user_id, answer)
        else:
            def generate_message():
                global set_context, current_topic, response, messages
                messages.append(f"{input_text}")
                response = palm.chat(**defaults, context=f'{set_context}', examples=EXAMPLES, messages=messages)
                answer = response.last
                current_topic = f"{answer}"
                send_back_message(user_id, answer)
        threading.Thread(target=generate_message).start()
        return "..."

@app.route('/SynochatPalm2', methods=['POST'])
def chatbot():
    token = SYNOCHAT_TOKEN
    webhook = OutgoingWebhook(request.form, token)
    if not webhook.authenticate(token):
        return webhook.createResponse('Outgoing Webhook authentication failed: Token mismatch.')
    input_text = webhook.text
    user_id = webhook.user_id
    return generate_response(input_text, user_id)

if __name__ == '__main__':
    app.run('0.0.0.0', port=FLASK_PORT, debug=False, threaded=True, processes=1)