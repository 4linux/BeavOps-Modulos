#!/usr/bin/python

from pymongo import MongoClient
import sys
import logging
import ConfigParser

class MongoOps:

	def __init__(self):
		try:
			config_parser = ConfigParser.ConfigParser()
			config_parser.read("/opt/4linux/beavops.ini")
			self.client = MongoClient(config_parser.get("mongodb",'mongo.server'))
			self.db = self.client[config_parser.get("mongodb","mongo.database")]
		except Exception as e:
			logging.error("[-] Falhou ao instanciar o modulo mongops %s",e)

	def CadastrarTurma(self,arquivo):
		try:
			res = self.db.turmas.find({'_id':arquivo['idCR4']}).count()
			if res:
				res = self.db.turmas.find({'_id':arquivo['idCR4']})
				logging.warning("[!] Turma ja cadastrada")
				for a in arquivo['alunos']:
					if not self.db.turmas.find({'_id':arquivo['idCR4'],'alunos.email':a['email']}).count():
						logging.warning("[!] Aluno novo encontrado: %s",a['email'])
						logging.info("[+] Cadastrando")
						self.db.turmas.update({'_id':arquivo['idCR4']},{"$addToSet":{"alunos":a}},upsert=True)
						self.db.turmas.update({'_id':arquivo['idCR4']},{"$set":{"status":0}},upsert=True)

				existentes  = self.db.turmas.find({'_id':arquivo['idCR4']})		
				for e in existentes:
					for a in e['alunos']:
						for j in arquivo['alunos']:
							if a['email'] in j['email']:
								break
						else:
							logging.warning("[!] Aluno removido da turma")
							self.db.turmas.update({'_id':arquivo['idCR4']},{"$set":{"status":0}},upsert=True)
							self.db.turmas.update({"_id":arquivo['idCR4'],"alunos.email":a['email']},{"$set":{"alunos.$.status":2}},upsert=True)

				for r in res:
					if r['dataDeConclusao'] != arquivo['dataDeConclusao']:
						logging.warning("[!] A data de conclusao do curso foi alterada")
						self.db.turmas.update({'_id':arquivo['idCR4']},{"$set":{"dataDeConclusao":arquivo['dataDeConclusao']}},upsert=True)
						self.db.turmas.update({'_id':arquivo['idCR4']},{"$set":{"DataFim":arquivo["DataFim"]}},upsert=True)
						logging.info("[+] Turma Reagendada")
					if r["dataDeInicio"] != arquivo['dataDeInicio']:
						logging.warning("[!] A data de inicio foi alterada")
						self.db.turmas.update({'_id':arquivo['idCR4']},{"$set":{"dataDeInicio":arquivo['dataDeInicio']}},upsert=True)
						self.db.turmas.update({'_id':arquivo['idCR4']},{"$set":{"DataInicio":arquivo["DataInicio"]}},upsert=True)
						logging.info("[+] Turma foi reagendada")
					if r["instrutor"] != arquivo['instrutor']:
						logging.warning("[!] O instrutor foi alterado")
						self.db.turmas.update({'_id':arquivo['idCR4']},{"$set":{"instrutor":arquivo['instrutor']}},upsert=True)
			else:
				self.db.turmas.insert(arquivo)
				logging.info("[+] Turma cadastrada no banco com sucesso")
		except Exception as e:
			logging.error("[-] Falhou ao cadastrar a turma no banco de dados %s",e)
	
	def AtualizarTurma(self,turma,update):
		try:
			self.db.turmas.update(turma,{"$set":update},upsert=True)
			logging.info("[+] Turma atualizada no banco de dados com sucesso")
		except Exception as e:
			logging.error("[-] Falhou ao remover a turma no banco de dados %s",e)

	def AtualizarAluno(self,turma,aluno):
		try:
			self.db.turmas.update({"_id":turma,"alunos.email":aluno},{"$set":{"alunos.$.status":1}},upsert=True)
			logging.info("[+] Status do aluno atualizado no banco de dados com sucesso")
		except Exception as e:
			logging.error("[-] Falhou ao atualizar status do aluno no banco de dados %s",e)

	def RemoverAluno(self,turma,aluno):
		try:
			self.db.turmas.update({"_id":int(turma),"alunos.idCR4":aluno['idCR4']},{"$pull":{"alunos":{"idCR4":aluno['idCR4']}}},multi=True)
			logging.info("[+] Aluno removido da turma no banco de dados com sucesso")
		except Exception as e:
			logging.error("[-] Falhou ao remover aluno da turma no banco de dados %s",e)

	def RemoverDoCurso(self,curso,aluno):
		try:
			self.db.turmas.update({"curso.idCR4":str(curso),"alunos.idCR4":aluno['idCR4']},{"$pull":{"alunos":{"idCR4":aluno['idCR4']}}},multi=True)
			logging.info("[+] Aluno removido da turma no banco de dados com sucesso")
		except Exception as e:
			logging.error("[-] Falhou ao remover aluno da turma no banco de dados %s",e)

	def RemoverTurma(self,turma):
		try:
			self.db.turmas.remove(turma)
			logging.info("[+] Turma removida do banco de dados com sucesso")
		except Exception as e:
			logging.error("[-] Falhou ao remover a turma no banco de dados %s",e)

	def BuscarTurma(self,turma):
		try:
			res = self.db.turmas.find(turma)
			return res
		except Exception as e:
			logging.error("[-] Falhou ao buscar a turma no banco de dados %s",e)

	def BuscarMilestones(self,curso):
		try:
			res = self.db.cursos.find(curso)
			return res
		except Exception as e:
			logging.error("[-] Falhou a buscar a milestones %s",e)

	def BuscarNomeDoCurso(self,curso):
		try:
			res = self.db.cursos.find({"curso":{"$regex":"%s"%curso}})
			for r in res:
				return r['curso']

		except Exception as e:
			logging.error("[-] Falhou ao buscar o nome do curso %s",e)
	
	def ListarMilestones(self):
		try:
			res = self.db.cursos.find()
			return res
		except Exception as e:
			logging.error("[-] Falhou ao listar todas as milestones %s",e)

	def ListarIssues(self,curso,title):
		try:
			res = self.db.cursos.find({"curso":curso,"milestones.title":title},{"_id":0})
			return res
		except Exception as e:
			logging.error("[-] Falhou ao buscar as issues %s",e)

	def RemovidosRecentes(self,turma):
		try:
			if self.db.recentes.find().count() > 7:
				self.db.recentes.remove({},-1)
			self.db.recentes.insert(turma)
			logging.info("[+] Turma cadastrada no removidos recentes")
		except Exception as e:
			logging.error("[-] Falhou ao cadastrar a turma no removidos recentes %s",e)

	def ListarRemovidosRecentes(self):
		try:
			res = self.db.recentes.find()
			return res
		except Exception as e:
			logging.error("[-] Fahlou ao buscar removidos recentes %s",e)

	def BuscarJobs(self,curso):
		try:
			res = self.db.cursos.find({"jenkins":"%s"%curso})
			return res
		except Exception as e:
			logging.error("[-] Falhou ao buscar Jobs %s",e)

	def BuscarRecursos(self,curso):
		try:
			res = self.db.recursos.find({"_id":int(curso)})
			return res
		except Exception as e:
			logging.error("[-] Nao foi possivel encontrar os recursos deste curso %s",e)

	def ListarRecursos(self):
		try:
			res = self.db.recursos.find()
			return res
		except Exception as e:
			logging.error("[-] Nao foi possivel listar os recusos %s",e)

	def BuscarTasks(self,curso):
		try:
			res = self.db.kanban.find({"cursos":int(curso)})
			return res
		except Exception as e:
			logging.error("[-] Erro ao buscar tasks %s",e)

	def BuscarModeloTask(self,modelo):
		try:
			res = self.db.kanban.find({"modelo":modelo})
			return res
		except Exception as e:
			logging.error("[-] Erro ao buscar modelo da task %s",e)

	def ListarTasks(self):
		try:
			res = self.db.kanban.find()
			return res
		except Exception as e:
			logging.error("[-] Erro ao listar as task: %s",e)

	def PegarUltimoCurso(self,aluno):
		try:
			res = self.db.turmas.find({"alunos.email":aluno}).sort("dataDeConclusao",-1).limit(1)
			return res
		except Exception as e:
			logging.error("[-] Falhou ao pegar ultimo curso do aluno %s",e)

	def AtualizarModeloTask(self,modelo,novo):
		try:
			self.db.kanban.update({'modelo':modelo},novo,upsert=True);
			logging.info("[+] Modelo atualizado com sucesso")
		except Exception as e:
			logging.error("[-] Erro ao atualizar o modelo da task %s",e)

	def RemoverModeloTask(self,modelo):
		try:
			self.db.kanban.remove({'modelo':modelo})
			logging.info("[+] Modelo removido com sucesso")
		except Exception as e:
			logging.error("[-] Erro ao remover task %s",e)

	def getAluno(self,email):
		try:
			res = self.db.turmas.find({"alunos.email":email,"status":1},{"_id":0,"curso":1,"alunos.$":1,"alunos":{"$slice":1}}).sort("dataDeConclusao",1).limit(1)
			return res
			logging.info("[+] Retornando informacoes do aluno")
		except Exception as e:
			logging.error("[-] Erro ao busca aluno %s",e)

	def PegarFormacao(self,curso):
		try:
			res = self.db.formacoes.find({"cursos":int(curso)})
			return res
		except Exception as e:
			logging.error("[-] Erro ao buscar formacao %s",e)

	def ListarFormacoes(self):
		try:
			res = self.db.formacoes.find()
			return res
		except Exception as e:
			logging.error("[-] Erro ao listar formacoes ")

	def MarcarPresenca(self,turma,aluno,nome,presenca):
		try:
			res = self.db.lista.find({"turma":int(turma),"aluno":aluno})
			if res.count():
				self.db.lista.update({"turma":int(turma),"aluno":aluno,"nome":nome},{"$addToSet":{"lista":presenca}},upsert=True)
			else:
				self.db.lista.insert({"turma":int(turma),"aluno":aluno,"nome":nome,"lista":[presenca]})
		except Exception as e:
			logging.error("[-] Falhou ao marcar presenca")

	def ListarPresenca(self,turma):
		try:
			res = self.db.lista.find({"turma":int(turma)})
			return res
		except Exception as e:
			logging.error("[-] Falhou ao listar a lista de presenca",e)

	def PresencaDoAluno(self,turma,aluno):
		try:
			res = self.db.lista.find({"turma":int(turma),"aluno":aluno},{"_id":0})
			return res
		except Exception as e:
			logging.error("[-] Falhou ao listar a lista de presenca do aluno %s",e)
