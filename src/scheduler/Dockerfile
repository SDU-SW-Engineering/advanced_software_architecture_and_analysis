FROM python:latest

# this will create a folder in docker image, and it's where we'll be working
WORKDIR /DockerScheduler

#Copy everything from this folder (scheduler) into /DockerScheduler, as we've specified that to be our working directory
COPY . ./

#Use this if we need to install something specific
#fx pip install flask (installs flask for python)
#RUN ....

#The main purpose of the CMD command is to start the process inside the container and it can be overridden.
# This command specifies to run the command 'python helloWorld.py'
CMD ["python", "./helloWorld.py"]

# Make sure your Docker daemon is running, before doing the following!!
# To build the image, run in terminal:
# docker build src/scheduler/Dockerfile

# To create and run a new container from the image
# docker run <ImageID OR tag you've given it>

# To automatically remove container and its volumes when it exits, run this
# CURRENTLY DOESNT WORK!! FIX
# docker run <ImageID OR tag you've given it> --rm