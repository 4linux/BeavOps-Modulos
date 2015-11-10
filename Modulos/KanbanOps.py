#!/usr/bin/python
# -*- coding: utf-8 -*-

import requests
import logging
import json
import sys
import datetime
import time
import ConfigParser
from MongoOps import MongoOps

class KanbanOps:
	def __init__(self):
		try:
			self.Board = ''

			config_parser = ConfigParser.ConfigParser()
			config_parser.read("/opt/4linux/beavops.ini")
			self.apiToken = config_parser.get("kanban",'kanban.apitoken')
			self.server = config_parser.get("kanban","kanban.server")

		except Exception as e:
			logging.error("[-] Nao foi possivel ler o arquivo de configuracao %s",e)		

	def PegarColunaId(self,nome):
		try:
			Board = requests.get("https://%s/api/v1/board?apiToken=%s"%(self.server,self.apiToken))

			colunas = json.loads(Board.text)['columns']

			for coluna in colunas:
				if coluna['name'] == nome:
					return coluna['uniqueId']

		except Exception as e:
			logging.error("[-] Erro, nao foi possivel pegar id da coluna %s".e)


	def CriarTask(self, **kwargs):
		try:
			json_data = {}
			
			if len(str(kwargs['curso'])) < 4:
				kwargs['modalidade'] = "Presencial"
			else:
				kwargs['modalidade'] = "EaD"

			TaskName = "%s - %s - %s - %s - %s"%(kwargs['turma'],kwargs['curso'],kwargs['modalidade'],kwargs['periodo'],kwargs['instrutor'])
		
			#-- Json da Task
			json_data['name'] = TaskName
			json_data['columnId'] = self.PegarColunaId('A Executar')
			json_data['color'] = 'cyan'
			#-- Fim Json da Task

			TaskId = requests.post("https://%s/api/v1/tasks?apiToken=%s"%(self.server,self.apiToken),
								data=json.dumps(json_data),
								headers={"Content-Type":"application/json"}
								)	
			return json.loads(TaskId.text)['taskId']
		except Exception as e:
			logging.error("[-] Falhou ao criar a task %s",e)

	def CriarSubTask(self, taskId, curso):
		try:
			mo = MongoOps()
			for res in mo.BuscarTasks(curso):
				for sub in res['subtask']:
					subtaskIndex = requests.post("https://%s/api/v1/tasks/%s/subtasks?apiToken=%s"%(self.server,taskId,self.apiToken),
											 data=json.dumps({"name":sub}),
											 headers={"Content-Type":"application/json"}
											 )
				break
			else:
				if len(str(curso)) < 4:
					for res in mo.BuscarModeloTask("principal-presencial"):
						for sub in res['subtask']:
							subtaskIndex = requests.post("https://%s/api/v1/tasks/%s/subtasks?apiToken=%s"%(self.server,taskId,self.apiToken),
												 data=json.dumps({"name":sub}),
												 headers={"Content-Type":"application/json"}
												 )
				else:
					for res in mo.BuscarModeloTask("principal-ead"):
						for sub in res['subtask']:
							subtaskIndex = requests.post("https://%s/api/v1/tasks/%s/subtasks?apiToken=%s"%(self.server,taskId,self.apiToken),
												 data=json.dumps({"name":sub}),
												 headers={"Content-Type":"application/json"}
												 )

		except Exception as e:
			logging.error("[-] Erro ao criar Subtasks %s",e)

	def PegarUsuario(self, responsavel):
		try:
			Usuarios = requests.get("https://%s/api/v1/users?apiToken=%s"%(self.server,self.apiToken))
			for u in json.loads(Usuarios.text):
				print u
				if u['email'] == responsavel:
					return u['_id']
		except Exception as e:
			logging.error("[-] Erro ao definir responsavel %s",e)

	def DefinirResponsavel(self,taskId,UsuarioId):
		try:
			label_retorno = requests.post("https://%s/api/v1/tasks/%s?apiToken=%s"%(self.server,taskId,self.apiToken),
											data=json.dumps({"responsibleUserId":UsuarioId}),
											headers={"content-type":"application/json"}
										)
		except Exception as e:
			logging.error("[-] Erro ao definir responsavel %s",e)

	def AdicionarColaborador(self,taskId,UsuarioId):
		try:
			colab_retorno = requests.post("https://%s/api/v1/tasks/%s/collaborators?apiToken=%s"%(self.server,taskId,self.apiToken),
											data=json.dumps({"userId":UsuarioId}),
											headers={"content-type":"application/json"}
										)

		except Exception as e:
			logging.error("[-] Erro ao adicionar colaborador %s",e)

	def CriarLabel(self,taskId,valor):
		try:
			label_retorno = requests.post("https://%s/api/v1/tasks/%s/labels?apiToken=%s"%(self.server,taskId,self.apiToken),
											data=json.dumps({"name":valor}),
											headers={"content-type":"application/json"}
										)
		except Exception as e:
			logging.error("[-] Erro ao criar Label %s",e)

	def CriarData(self, taskId, di, df):
		try:

			DataInicioCurso = datetime.datetime.fromtimestamp(di/1000)
			DataFimCurso = datetime.datetime.fromtimestamp(df/1000)
			DataInProgress = DataInicioCurso - datetime.timedelta(7)
			DataDone = DataFimCurso + datetime.timedelta(7)

			utc = time.strftime("%Y-%m-%dT%H:%M:%SZ",time.gmtime(time.mktime((DataInProgress).timetuple())))
			json_data = {"dueTimestamp":utc,"targetColumnId":self.PegarColunaId('A Executar')}
			
			dataInicio = requests.post("https://%s/api/v1/tasks/%s/dates?apiToken=%s"%(self.server,taskId,self.apiToken),
										data=json.dumps(json_data),
										headers={"content-type":"application/json"}
									)

			utc = time.strftime("%Y-%m-%dT%H:%M:%SZ",time.gmtime(time.mktime((DataDone).timetuple())))
			json_data = {"dueTimestamp":utc,"targetColumnId":self.PegarColunaId('Finalizada')}
			dataFim = requests.post("https://%s/api/v1/tasks/%s/dates?apiToken=%s"%(self.server,taskId,self.apiToken),
										data=json.dumps(json_data),
										headers={"content-type":"application/json"}
									)
			print dataFim.text

		except Exception as e:
			logging.error("[-] Erro ao criar data %s",e)

