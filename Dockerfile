FROM ubuntu:16.04

# install pip
RUN apt-get update
RUN apt-get -y install python-pip python-dev build-essential
RUN pip install --upgrade pip

# special dependency for scipy image utils
# not in requirements.txt because that could mess up other envs
RUN pip install Pillow

# copy repo over
COPY . /home/ubuntu/dcgan-completion.tensorflow

# install requirements
RUN pip install -r /home/ubuntu/dcgan-completion.tensorflow/requirements.txt

ENTRYPOINT ["/home/ubuntu/dcgan-completion.tensorflow/train-dcgan.py", \
	   "--dataset", "/home/ubuntu/dcgan-completion.tensorflow/data/MS-Celeb-1M-P1/aligned/", \
	   "--epoch", "1"]
