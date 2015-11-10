#!/usr/bin/python
# -*- coding: utf-8 -*-

from elementtree.ElementTree import parse,Element,SubElement
import uuid
from xml.etree import ElementTree
from xml.dom import minidom
import sys
import os
from requests.auth import HTTPBasicAuth
import requests
import logging
import paramiko

from MongoOps import MongoOps

log = logging.getLogger(__name__)

class JenkinsOps:
	def __init__(self):
		with open("/opt/4linux/beavops.ini",'r') as config:
			for c in config.readlines():
				if "jenkins.server" in c:
					self.servidor = c.split("=")[1].strip()
				elif "jenkins.user" in c:
					self.usuario = c.split("=")[1].strip()
				elif "jenkins.password" in c:
					self.senha = c.split("=")[1].strip()

	def CriarJob(self,Aluno,Curso,Repo,CredentialId):
		"""
			Método que cria as jobs do usuario no jenkins live de acordo com o curso, elas ficam armazenadas em /var/lib/jenkins/jobs . Exste 1 diretório para cada Job, caso uma job já exista com o mesmo nome ela não será sobrescrita.
			Os nomes das jobs ficam armazenados em um bancos de dados NoSQL (mongodb) em devops.4linux.com.br
			As jobs são baseadas em templates de arquivos xml que podem ser encontrados em /opt/4linux/Templates/ a job template precisa ter o mesmo numero do curso.

			:param Aluno: Aluno precisa ser um dicionario com no mínimo 2 keys: email,username.
			:param Curso: Curso precisa ser o número do curso do aluno
			:param Repo:  Repo é uma string com o repositório do aluno no gitlab, precisa ser o endereço para fazer o clone via ssh
			:param CredentialId: CredentialId é uma string com o UUID gerado conforme a credential é criada no jenkins, ela pode ser criada pela interface do jenkins ou  no método CriarCredential do módulo JenkinsOps
			:returns: Esse método não possui valor de retorno

		"""
		try:
			mo = MongoOps()
			NomeCurso = mo.BuscarNomeDoCurso(Curso)
			res = mo.BuscarJobs('%s'%NomeCurso)
		except Exception as e:
			log.error("[-] Erro ao conectar com o banco de dados %s",e)
			sys.exit(1)
		for r in res:
			for j in r['jobs']:
				try:
					with open("/opt/4linux/Templates/%s.xml"%Curso,"r") as f:
						JobTemplate = f.read().replace("ALUNO",Aluno['email']) \
											.replace("REPO",Repo) \
											.replace("CREDENTIALID",CredentialId) \
											.replace("IDCR4",Aluno['username']) \
											.replace("NOMELAB",j['title']) \
											.replace("CURSO",Curso)
					f.close()

					try:
						retorn = requests.post("http://%s/createItem?name=%s-%s-%s"%(self.servidor,Curso,Aluno['username'],j['title'].replace(" ","%20")),
										data=JobTemplate,
										auth=HTTPBasicAuth(self.usuario,self.senha),
										headers={"Content-Type":"application/xml"}
									)
					except Exception as e:
						log.error("[-] Nao foi possivel criar a job %s",e)

					
					try:
						ssh = paramiko.SSHClient()
						ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
						ssh.connect(self.servidor.split(":")[0],port=38844,username=self.usuario,key_filename="/opt/4linux/chaves/4linux.devops@4linux.com.br")
						stdin, stdout, stderr = ssh.exec_command("add-job-to-view %s '%s-%s-%s'"%(Curso,Curso,Aluno['username'],j['title'].replace(" ","\ ")))
						ssh.close()
					except Exception as e:
						log.error("[-] Falhou ao adicionar job a view %s",e)

					log.info("[+] Job %s Criada com Sucesso",j['title'])
				except Exception as e:
					log.error("[-] Erro ao criar Job %s",e)

	def RemoverJobs(self,Aluno,Curso):
		try:
			try:
				mo = MongoOps()
				NomeCurso = mo.BuscarNomeDoCurso(Curso)
				res = mo.BuscarJobs("%s"%NomeCurso)
			except Exception as e:
				log.error("[-] Erro ao conectar com o banco de dados %s",e)
				sys.exit(1)
			for r in res:
				for j in r['jobs']:
					log.info("Removendo job %s",j['title'])
					response = requests.post("http://%s/job/%s-%s-%s/doDelete"%(self.servidor,Curso,Aluno,j['title'].replace(" ","%20")),
										auth=HTTPBasicAuth(self.usuario,self.senha)
							)
			else:
				log.info("[+] Jobs removidas com sucesso")
		except Exception as e:
			log.error("[-] Falha ao remover as jobs %s",e)

	def AdicionarUsuario(self,Aluno):
		"""
			Método que cria o usuário no jenkins, atualmente o jenkins está vinculado com o ldap do sistema ead, por mais que o usuário esteja criado no jenkins, ele não conseguirá autenticar se não estiver cadastrado no LDAP também.
			Para fazer o cadastro do aluno é adicionada mais uma linha do /var/lib/jenkins/config.xml dentro das tags <permission> somente com permissão de leitura.

			:param Aluno: Aluno é uma string somente com o email do aluno.

			:returns: Esse método não possui valor de retorno
		"""
		try:
			tree = parse("/var/lib/jenkins/config.xml")
			elem = tree.getroot()
			perm = elem.find('authorizationStrategy')
			busca = perm.findall("permission")
			for b in busca:
				if Aluno in b.text:
					log.warning("[!] Usuario Ja cadastrado no jenkins")
					return
			user = Element("permission")
			user.text = "hudson.model.Hudson.Read:%s"%Aluno
			perm.append(user)
			tree.write("/var/lib/jenkins/config.xml")
			log.info("[+] Usuario %s adicionado ao jenkins com Sucesso",Aluno)
		except Exception as e:
			log.error("[-] Erro ao adicionar usuario ao jenkins %s",e)

	def RemoverUsuario(self,Aluno):
		try:
			tree = parse("/var/lib/jenkins/config.xml")
			elem = tree.getroot()
			perm = elem.find('authorizationStrategy')
			busca = perm.findall('permission')
			for b in busca:
				if b.text == "hudson.model.Hudson.Read:%s"%Aluno:
					perm.remove(b)
					log.info("[+] Usuario %s removido",Aluno)
					break
			else:
				log.warning("[!] Usuario nao encontrado no Jenkins")
			tree.write("/var/lib/jenkins/config.xml")
		except Exception as e:
			log.error("[-] Erro ao remover o usuario %s ",e)

	def CriarCredential(self, Aluno, Chave):
		"""
			Método que cria a credential do aluno para que o jenkins possa conectar no gitlab e fazer o git clone do projeto do aluno

			:param Aluno: Aluno é uma string contendo o email do aluno que será o nomer da credential
			:param Chave: Chave é uma string contendo a chave privada para a autenticação no gitlab.

			:returns: Esse método retorno o ID da credential criada para que ele possa ser vinculado na job.
		"""
		try:
			tree = parse("/var/lib/jenkins/credentials.xml")
			elem = tree.getroot()
			domain = elem.find("domainCredentialsMap")
			entry = domain.find("entry")
			Permissions = entry.find("java.util.concurrent.CopyOnWriteArrayList")
			chaveUsuario = Permissions.findall("com.cloudbees.jenkins.plugins.sshcredentials.impl.BasicSSHUserPrivateKey")
			for c in chaveUsuario:
				busca = c.findall("username")
				ids = c.findall("id")
				for b in busca:
					if Aluno in b.text:
						log.warning("[!] Credential deste aluno ja existe")
						return ids[busca.index(b)].text
			CXML = Element("com.cloudbees.jenkins.plugins.sshcredentials.impl.BasicSSHUserPrivateKey",plugin="ssh-credentials@1.11")
			NodeScope = Element("scope")
			NodeScope.text = "GLOBAL"
			CXML.append(NodeScope)
			NodeId = Element("id")
			NodeId.text = str(uuid.uuid1())
			CXML.append(NodeId)
			NodeDesc = Element("description")
			CXML.append(NodeDesc)
			NodeUsername = Element("username")
			NodeUsername.text = Aluno
			CXML.append(NodeUsername)
			NodePassphrase = Element("passphrase")
			NodePassphrase.text = "ITkJ2nM+QRH/rnQJFb/h7kDKXnkpDW2TtMs5fstXnxQ="
			CXML.append(NodePassphrase)
			NodePrivateKeySource = Element("privateKeySource",{"class":"com.cloudbees.jenkins.plugins.sshcredentials.impl.BasicSSHUserPrivateKey$DirectEntryPrivateKeySource"})
			NodePrivateKey = Element("privateKey")
			NodePrivateKey.text = str(Chave)
			NodePrivateKeySource.append(NodePrivateKey)
			CXML.append(NodePrivateKeySource)
			
			#Identando XML
			XMLString = ElementTree.tostring(CXML)
			XMLIndentado = minidom.parseString(XMLString).toprettyxml()
			with open("/tmp/temp.xml","w") as f:
				f.write(XMLIndentado)
			f.close()
			#fim da identacao
			
			ArqXML = open("/tmp/temp.xml","r")
			XMLTemp = parse(ArqXML)
			Credential = XMLTemp.getroot()
			Permissions.append(Credential)
			tree.write("/var/lib/jenkins/credentials.xml")
			log.info("[+] Credential criada com sucesso")
			return NodeId.text
		except Exception as e:
			log.error("[-] Erro ao criar credential %s",e)
			return False

	def RemoverCredential(self,Aluno):
		try:
			tree = parse("/var/lib/jenkins/credentials.xml")
			elem = tree.getroot()
			domain = elem.find("domainCredentialsMap")
			entry = domain.find("entry")
			Permissions = entry.find("java.util.concurrent.CopyOnWriteArrayList")
			chaveUsuario = Permissions.findall("com.cloudbees.jenkins.plugins.sshcredentials.impl.BasicSSHUserPrivateKey")
			encontrou = 0
			for c in chaveUsuario:
				if encontrou == 1:
					break
				busca = c.findall("username")
				for b in busca:
					if Aluno in b.text:
						Permissions.remove(c)
						log.info("[+] Credential do aluno %s removida",Aluno)
						encontrou = 1
						break
			else:
				if encontrou == 0:
					log.warning("[!] Credential nao encontrada")
			tree.write("/var/lib/jenkins/credentials.xml")
		except Exception as e:
			log.error("[-] Erro ao remover a credential %s",e)

	def doReload(self):
		try:
			os.system("service jenkins restart")
		except Exception as e:
			log.error("[-] Nao foi possivel fazer o safeRestart do Jenkins %s",e)

