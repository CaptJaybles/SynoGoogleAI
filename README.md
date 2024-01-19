# SynoGoogleAI V1.0
Using GoogleAI Gemini and Palm api with synology chat

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

  1) Copy your google AI api key into the settings GOOGLEAI_API_KEY
  
  2) setup a new bot in your synology chat app
  
  3) copy the Token and the incoming URL to the settings file
  
  4) the outgoing URL in synology integration will be http://IP_ADDRESS:FLASK_PORT/SynoGoogleAI change IP_ADDRESS to what it is on your local PC your running the model on

  4a) if installing to synology nas itself see belore the outgoing URL will be something like this http://127.0.0.1:5015/SynoGoogleAI depending on your port you use
  
  5) Use either SynoGoogleAI.bat file or command
  
    python SynoGoogleAI.py


Features


Select between using Gemini or Palm models in settings (default is gemini)
  
     /model gemini|palm

Gemini Features

  1) Conversation reset command

     /reset
     
  2) Rewind your conversation back one exchange

     /rewind

Palm Features

  1) context and conversation reset command 
      
    /reset
  
  2) set a temporary context without having to change it in settings, will reset back to none on a /reset or script exit
      
    /context
    
  3) input prompt override to use palm generate instead of palm chat, safety filters have been disabled with this command

    /override



Install this on your synology nas and run from nas
  1) install python from package center, python3.10 recomended
  2) create directory and place files onto NAS
  3) Make sure you make the proper changes to the settings file
  4) ssh into NAS
  5) go to directory folder ie cd /volume1/FOLDER
  6) python3.10 -m venv venv
  7) . venv/bin/activate
  8) pip install -r requirements.txt
  9) Open control Panel app on NAS
  10) navigate to task schedualer
  11) select create, triggered task, user-defined script
  12) Give it a task name like SynoGoogleAI
  13) Select task settings and paste something like this
      
      cd /volume1/chat/SynoGoogleAI
      
      . venv/bin/activate
      
      python3.10 SynoGoogleAI.py

  14) select ok and it should be running
