ARG IMAGE_VERSION
FROM python:${IMAGE_VERSION}
ARG INSTALL_ASYNC

WORKDIR /usr/src/app
COPY ./code /usr/src/app/code


RUN echo "INSTALL_ASYNC is" 
RUN echo "$INSTALL_ASYNC"
RUN if [ "$INSTALL_ASYNC" = "yes" ] ; then pip install aiohttp cchardet aiodns ; else echo "not python3 so wont install aiohttp" ; fi
