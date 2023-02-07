FROM selenium/standalone-chrome

# install python 3.10 and others
RUN sudo apt update
RUN sudo apt install -y --no-install-recommends software-properties-common
RUN sudo add-apt-repository ppa:deadsnakes/ppa
RUN sudo apt install -y --no-install-recommends python3.10 python3.10-venv git wget

# set working dir to home dir
WORKDIR /home/seluser

# install pip
RUN wget https://bootstrap.pypa.io/get-pip.py
RUN python3.10 get-pip.py

# create venv
ENV VIRTUAL_ENV=/home/seluser/venv310
RUN python3.10 -m venv $VIRTUAL_ENV

# activate venv
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

WORKDIR discord_bot

# install requirements
COPY requirements.txt .
RUN python -m pip install -r requirements.txt

# copy files
RUN mkdir cache
COPY . .

CMD ["python", "wörterbuch_bot.py"]