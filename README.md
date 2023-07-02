# SynochatPalm2
Using google Palm2 api with synology chat

Install
  
  1) aquire google ai api key
  
  2) clone repository
  
  3) create virtual envirement in folder    
    
    python -m venv venv
  
  4) activate virual envirement             
  
    venv/Scripts/activate
 
  5) install the requirements
    
    pip install -r requirements.txt

Setup

  1) Copy your google AI api key into the settings PALM_API_KEY
  
  2) setup a new bot in your synology chat app
  
  3) copy the Token and the incoming URL to the settings file
  
  4) the outgoing URL in synology integration will be http://IP_ADDRESS:FLASK_PORT/SynochatPalm2 change IP_ADDRESS to what it is on your local PC your running the model on
  
  5) Use either synochatPalm2.bat file or command
  
    python synochatPalm2.py

Features
  
  1) Talk to any google api model by changing the model in settings
  
  2) It has a model reset if the conversation strays command    
      
    /reset
  
  3) set a temporary context without having to change it in settings, will reset back to none on a /reset or script exit
      
    /context
    
  4) added prompt override to use palm generate instead of palm chat

    /override
