#!/usr/bin/python
#-*- coding: utf-8 -*-

import gitlab
import json
import sys
import os
from pymongo import MongoClient
import time
import pexpect
from MongoOps import MongoOps
import logging
import ConfigParser

log = logging.getLogger(__name__)


class GitlabOps:
	"""
		Módulo que realiza todas as operações do gitlab
	"""

	def __init__(self):
		"""
			Método Construtor que efetua o login no gitlab para realizar as operações
		"""
		try:
			config_parser = ConfigParser.ConfigParser()
			config_parser.read("/opt/4linux/beavops.ini")
			self.servidor = config_parser.get("gitlab","gitlab.server")
			self.usuario = config_parser.get("gitlab","gitlab.user")
			self.senha = config_parser.get("gitlab","gitlab.password")
		except Exception as e:
			logging.error("[-] Falhou ao recuperar dados de acesso do gitlab %s",e)

		try:
			self.git = gitlab.Gitlab("http://%s"%self.servidor,verify_ssl=False)
			self.git.login(user=self.usuario,password=self.senha)
		except Exception as e:
			log.error("[-] Falha ao logar no gitlab %s",e)

	def CriarUsuario(self,Usuario):
		"""
			Método que cria o usuário

			:param Usuario: Usuario e um dicionário que precisa de 3 keys: name, username, email. Exemplo: {'name':'Alisson Machado','username':'123456','email':'alisson.machado@4linux.com.br'}

			:returns: Esse método não possui retorno, apenas gera um log informando se o usuario já foi criado com sucesso ou não
		"""
		try:
			if not self.git.createuser(Usuario['name'],Usuario['username'],Usuario['password'],Usuario['email'],confirm="false"):
				log.info("[!] Usuario ja existe %s",Usuario['email'])
		except Exception as e:
			log.error("[-] Erro ao criar o usuario %s",e)

	def RemoverUsuario(self,Usuario):
		try:
			for u in self.git.getusers(search=Usuario['email']):
				if self.git.deleteuser(u['id']):
					log.info("[+] Usuario removido com sucesso")
					break
				else:
					log.error("[-] Nao foi possivel remover o usuario")
			else:
				log.warning("[!] Usuario nao encontrado")
		except Exception as e:
			log.error("[-] Erro ao remover o usuario %s",e)

	def RemoverProjeto(self,Usuario,Curso):
		log.info("[+] Procurando projetos a serem removidos")
		try:
			for u in self.git.getusers(search=Usuario['email']):
				self.git.setsudo(int(u['id']))
				projs = self.git.getprojectsowned()
				for p in projs:
					if "%s-PHP"%Curso in p['name'] or "%s-FrontEnd"%Curso in p['name']:
						log.warning("[!] Projeto encontrado")
						self.git.deleteproject(p['id'])
						log.info("[+] Projeto removido")
		except Exception as e:
			log.error("[-] Falhou ao remover o projeto %s",e)

	
	def CriarProjeto(self,Usuario,Curso):
		"""
			Método que cria o projeto do usuário baseado no numero do curso

			:param Usuario: Usuario precisa ser um dicionário com 3 keys: name,username,email. Exemplo: {'name':'Alisson Machado','username':'123456','email':'alisson.machado@4linux.com.br'}

			:param Curso: Curso e uma variavel que precisa ter somente o numero do curso que o aluno ira fazer.	Exemplo: 4501

			:returns: Retorna um dicionário com todas as informacoes sobre o projeto. Algumas chaves de exemplo sao: ssh_url_to_repo, id, http_url_to_repo, etc.
		"""
		mo = MongoOps()
		NomeCurso = mo.BuscarNomeDoCurso(Curso)

		for u in self.git.getusers(search="4linux.devops@4linux.com.br"):
			self.adminuser = u['id']
		try:
			for u in self.git.getusers(search=Usuario['email']):
				#loga como o usuario
				self.git.setsudo(int(u['id']))
				projs = self.git.getprojectsowned()
				#Verifica se projeto ja existe
				for p in projs:
					if "%s"%NomeCurso in p['name']:
						log.warning("[!] O Projeto ja existe")
						log.warning("[!] Deletando o projeto")
						self.git.deleteproject(p['id'])
				log.info("[+] Criando o projeto")

				for i in range(2,6):
					if self.git.createproject("%s"%NomeCurso,path="%s"%NomeCurso):
						log.info( "[+] Projeto Criado com Sucesso!")
						break
					else:
						log.warning("[!] Falhou ao criar projeto, Tentativa - %i",i)
						time.sleep(1)
				else:
					log.error("[-] Nao foi possivel criar o projeto")
					log.error("[-] Saindo do Script")
					sys.exit()
			else:
				log.error("[-] Nao foi encontrado nenhum curso com o numero %s",Curso)

			#pega primeiro projeto do usuario
			projeto = self.git.getprojectsowned()[0]
			project_id = int(self.git.getprojectsowned()[0]['id'])
			log.info("[+] Adicionando usuario 4linux ao projeto")
			if not self.git.addprojectmember(project_id,str(self.adminuser),"master"):
				log.error("[-] Erro ao adicionar membro ao projeto")
			return projeto
				
		except Exception as e:
			log.error("[-] Erro ao criar projeto %s",e)

	def AdicionarChaveAoGitlab(self,Usuario,Chave):
		"""
			Método que adiciona a chave do usuário no gitlab para que o jenkins possa fazer o deploy no ambiente live.

			:param Usuario: Esse parâmetro precisa ser um dicionário com 3 keys: name,username,email. Exemplo: {'name':'Alisson Machado','username':'123456','email':'alisson.machado@4linux.com.br'}

			:param Chave: A variável precisa ser uma chave pública que pode ser gerada a partir do comando ssh-keygen, atualmente ela e gerada pelo modulo UtilOps.
			
			:returns: Função não possui retorno, apenas gera um log informando se a chave foi cadastrada com sucesso ou não.
		"""
		try:
			for u in self.git.getusers(search=Usuario['email']):
				self.git.setsudo(int(u['id']))
				if self.git.addsshkey("ChaveJenkinsLive",Chave):
					log.info("[+] Chave do Jenkins Live cadastrada com sucesso")
				else:
					log.warning("[!] Atencao: Ja existe esta chave cadastrada")
		except Exception as e:
			log.error("[-] Falha ao cadastrar chave %s",e)
		

	def CriarMilestones(self,Aluno,Curso,ProjectId):
		"""
			Método que cria as milestones e issues do aluno

			:param Aluno: Usuario precisa ser um dicionário com 3 keys: name,username,email. Exemplo: {'name':'Alisson Machado','username':'123456','email':'alisson.machado@4linux.com.br'}

			:param Curso: Curso e uma variável que precisa ter somente o número do curso que o aluno irá fazer

			:param ProjectId: ProjectId é o id do projeto no gitlab.
	
			:returns: Método não possui valor de retorno, apenas mostra os ids das milestones e issues criadas durante a execução do método

		"""
		try:
			mo = MongoOps()
			NomeCurso = mo.BuscarNomeDoCurso(Curso)

			Retorno = mo.BuscarMilestones({"curso":"%s"%NomeCurso})
			log.info("[+] Buscando milestones")
		except Exception as e:
			log.error("[-] Nao foi possivel conectar com o banco %s",e)
			sys.exit()
		log.info("[+] Criando Milestones para o aluno %s",Aluno['email'])
		try:
			for r in Retorno:
				for m in reversed(r['milestones']):
					for num in range(2,6):
						if not self.git.createmilestone(ProjectId,m['title'],description=m['description']):
							log.error("[-] Falhou ao criar milestones - Tentativa %s",num)
						else:
							break
					mid = self.git.getmilestones(ProjectId)[0]['id']
					log.info("[+] Milestone: %s",mid)
					for i in reversed(m['issues']):
						#Cria Issues no projeto
						for num in range(2,6):
							issue = self.git.createissue(ProjectId,i['title'])
							if not issue:
								log.error("[-] Falhou ao criar issue - Tentativa %s",num)
							else:
								break
						self.git.editissue(ProjectId,issue['id'],milestone_id=mid,description=i['description'])
						log.info("[+] Criando issue %s",issue['id'])
		except Exception as e:
			log.error("[-] Falhou ao criar as milestones %s",e)
		log.info("[+] Fim da criacao de milestones")

	def SubirProjeto(self,Aluno,Curso,Projeto):
		"""
			Método que sobe os arquivos para o repositorio do aluno

			:param Aluno: Usuario precisa ser um dicionário com 3 keys: name,username,email. Exemplo: {'name':'Alisson Machado','username':'123456','email':'alisson.machado@4linux.com.br'}

			:param Curso: Curso e uma variavel que precisa ter somente o numero do curso que o aluno ira fazer

			:param Projeto: Precisa ser um dicionário com pelo menos 2 chaves, ssh_url_to_repo e id, que são as informações necessárias para fazer o git push dos arquivos para o projeto do launo
	
			:returns: Método não possui valor de retorno, apenas informa na tela a porcentagem do upload dos arquivos

		"""

		mo = MongoOps()
		NomeCurso = mo.BuscarNomeDoCurso(Curso)

		log.info( "[+] Subindo projeto")
		try:
			os.chdir("/opt/4linux/%s"%NomeCurso)
			pexpect.run("git add --all")
			pexpect.run("git commit --amend")
			cmd = pexpect.spawn("git push %s master -f"%Projeto['ssh_url_to_repo'])
			cmd.expect(pexpect.EOF)
		except Exception as e:
			log.error("[-] Erro ao subir o projeto: %s",e)
		log.info("[+] Removendo o usuario 4linux do projeto")
		if not self.git.deleteprojectmember(int(Projeto['id']),str(self.adminuser)):
			log.error("[-] Erro ao remover membro do projeto %s",e)

	def AdicionarWebHook(self,projetoid,url):
		"""
			Método que cria a webhook no projeto do aluno para acionar as jobs do jenkins live.

			:param projetoid: projetoid precisa ser o id do projeto do usuário no gitlab
			
			:param url: url é a url do jenkins que vai acionar as jobs
	
			:returns: Método não possui valor de retorno, apenas informa se a webhook foi adicionada ou não

		"""

		try:
			if self.git.addprojecthook(projetoid,url,push=True):
				log.info( "[+] WebHook Cadastrada com sucesso")
			else:
				log.error( "[-] Falhou, verifique se a web hook ja esta cadastrada")

		except Exception as e:
			log.error( "[-] Falhou ao cadastrar a WebHook %s",e)



