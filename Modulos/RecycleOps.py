#!/usr/bin/python

from UtilOps import UtilOps
from JenkinsOps import JenkinsOps
from GitlabOps import GitlabOps
from MongoOps import MongoOps
from LdapOps import LdapOps
from DockerOps import DockerOps
import logging

class RecycleOps:
	"""
		Classe criada para limpar o ambiente EaD
	"""
	def LimparAluno(self,Aluno,Curso):
		Aluno['username'] = str(Aluno['idCR4'])
		Aluno['name'] = Aluno['nome']

		if len(str(Curso)) < 4:
			logging.info("[+] Removendo Aluno do Curso Presencial")
			Curso = "4%s"%str(Curso)

		# importando modulos
		mo = MongoOps()
		uo = UtilOps()
		recursos = mo.BuscarRecursos(Curso)
		try:
			logging.info("[+] Limpando ambiente do aluno")
			ldapops = LdapOps()
			ldapops.RemoverUsuarioDoGrupo(Aluno['email'],Curso)
			for rec in recursos:
				if rec['apache'] == 1:
					uo.RemoverPaginaDefault(Aluno['username'])
				if rec['gitlab'] == 1:
					gl = GitlabOps()
					gl.RemoverProjeto(Aluno,Curso)
				if rec['jenkins'] == 1:
					jk = JenkinsOps()
					jk.RemoverUsuario(Aluno['email'])		
					jk.RemoverCredential(Aluno['email'])
					jk.RemoverJobs(Aluno['username'],Curso)
				if rec['docker'] == 1:
					dockerops = DockerOps()
					dockerops.RemoverContainer(str(Aluno['idCR4']))
		except Exception as e:
			logging.error("[-] Falha ao limpar o ambiente %s",e)

	def LimparTurma(self,Aluno,Curso):
		Aluno['username'] = str(Aluno['idCR4'])
		Aluno['name'] = Aluno['nome']
		logging.info("[!] Removendo curso %s",Curso)

		if len(str(Curso)) < 4:
			logging.info("[+] Removendo Curso Presencial")
			Curso = "4%s"%str(Curso)

		# importando modulos
		mo = MongoOps()
		logging.info("Considerando %s",Curso)
		formacao = mo.PegarFormacao(Curso)

		if formacao.count():
			for form in formacao:
				logging.info("[!] O Curso dessa turma faz parte da formacao %s , serao removidos os anteriores da mesma formacao",form["_id"])
				for f in form['cursos']:
					if int(Curso) >= int(f):
						recursos = mo.BuscarRecursos(f)
						try:
							logging.info("[+] Removendo Curso %i"%f)
							self.LimparAluno(Aluno,int(f))
						except Exception as e:
							logging.error("[-] Falha ao limpar o ambiente %s",e)
		else:
			try:
				logging.info("[+] Limpando Turma")
				recursos = mo.BuscarRecursos(Curso)
				for rec in recursos:
					if rec['apache'] == 1:
						uo = UtilOps()
						uo.RemoverPaginaDefault(Aluno['username'])
					if rec['gitlab'] == 1:
						gl = GitlabOps()
						gl.RemoverUsuario(Aluno)
					if rec['jenkins'] == 1:
						jk = JenkinsOps()
						jk.RemoverUsuario(Aluno['email'])		
						jk.RemoverCredential(Aluno['email'])
						jk.RemoverJobs(Aluno['username'],Curso)
					if rec['docker'] == 1:
						dockerops = DockerOps()
						dockerops.RemoverContainer(str(Aluno['idCR4']))
			except Exception as e:
					logging.error("[-] Falha ao limpar o ambiente %s",e)

