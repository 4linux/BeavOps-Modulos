#!/usr/bin/python

from docker import Client
from io import BytesIO
import logging

class DockerOps:

	def __init__(self):
	   try:
            config_parser = ConfigParser.ConfigParser()
            config_parser.read("/opt/4linux/beavops.ini")
            self.docker = Client(base_url=config_parser.get("docker","docker.server"))
        except Exception as e:
            logging.error("[-] Falhou ao conectar na api %s",e)

	def MostrarContainers(self):
		for d in self.docker.containers():
			print d['Names'], d['Id']

	def CriarContainer(self,aluno):
		try:
			logging.info("[+] Criando Container do aluno %s",aluno)
			container = self.docker.create_container(image="webservercloud",hostname="webservercloud", command="/bin/bash",name=aluno,tty=True)
			print container.get("Id")
			response = self.docker.start(container=container.get("Id"))
		except Exception as e:
			logging.error("[-] Falhou ao criar o container %s",e)

	def RemoverContainer(self,aluno):
		try:
			container = self.docker.stop(container=aluno)
			container = self.docker.remove_container(container=aluno)
			logging.info("[+] Removendo Container do aluno %s",aluno)
		except Exception as e:
			logging.error("[-] Erro ao remover o container %s",e)

if __name__ == '__main__':
	do = DockerOps()
	#do.MostrarContainers()
	do.CriarContainer("teste")
