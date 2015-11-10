#!/usr/bin/python

import logging
import ldap
import ldap.modlist
import ConfigParser

log = logging.getLogger(__name__)

class LdapOps:
	def __init__(self):
		try:
			config_parser = ConfigParser.ConfigParser()
			config_parser.read("/opt/4linux/beavops.ini")
			self.servidor = config_parser.get("ldap",'ldap.server')
			self.usuario = config_parser.get("ldap",'ldap.user')
			self.senha = config_parser.get("ldap",'ldap.password')

		except Exception as e:
			print("[-] Nao foi possivel ler o arquivo de configuracao %s",e)		

		try:
			self.ldap = ldap.initialize("ldap://%s"%self.servidor)
			self.ldap.protocol_version = ldap.VERSION3
			self.ldap.bind(self.usuario,self.senha)
		except ldap.LDAPError as e:
			print("[-] Nao foi possivel conectar a base ldap %s"%e)			

	def AdicionarUsuarioAoGrupo(self,aluno,curso):
		log.info("[+] Adicionando o aluno %s",aluno)
		entry = str("mail="+aluno+",ou=user,dc=ead4linux")
		attr = [(ldap.MOD_ADD, 'member', entry)]
		try:	
			self.ldap.modify_s(str("cn=%s,ou=groups,dc=ead4linux"%curso), attr)
			log.info("[+] Usuario adicionado ao grupo")
		except ldap.LDAPError as e:
			log.info("[-] Falhou ao adicionar o usuario no grupo Developer %s",e.message['info'])

	def RemoverUsuarioDoGrupo(self,aluno,curso):
		log.info("[+] Removendo o aluno %s",aluno)
		entry = str("mail="+aluno+",ou=user,dc=ead4linux")
		attr = [(ldap.MOD_DELETE, 'member', entry)]
		try:	
			self.ldap.modify_s(str("cn=%s,ou=groups,dc=ead4linux"%curso), attr)
			log.info("[+] Usuario removido do grupo")
		except ldap.LDAPError as e:
			log.info("[-] Falhou ao remover o usuario no grupo Developer %s",e.message['info'])

		
