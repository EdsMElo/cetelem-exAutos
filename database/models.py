from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class Process(Base):
    __tablename__ = 'processes'
    
    id = Column(Integer, primary_key=True)
    external_id = Column(Integer)  # ID original do sistema (218158)
    numero = Column(String(50))       # Número do processo (0001019-11.2019.8.06.0203)
    parte_adversa = Column(String(200))  # Nome da parte adversa
    cpf_cnpj_parte_adverso = Column(String(20))  # CPF/CNPJ da parte adversa
    comarca = Column(String(100))
    estado = Column(String(50))
    escritorio_celula = Column(String(200))  # Escritório
    status = Column(String(50))
    fase = Column(String(100))
    advogados_adversos = Column(String(500))  # Lista de advogados
    tem_acordo = Column(Boolean)  # Campo Acordo (Sim/Não)
    suspeita_fraude = Column(Boolean)  # Campo Suspeita de Fraude (Sim/Não)
    data_cadastro = Column(DateTime)  # Data de cadastro do processo
    created_at = Column(DateTime, default=datetime.now)
    
    # Relacionamentos
    agreements = relationship("Agreement", back_populates="process", cascade="all, delete-orphan")
    fraud_assessments = relationship("FraudAssessment", back_populates="process", cascade="all, delete-orphan")

class Agreement(Base):
    __tablename__ = 'agreements'
    
    id = Column(Integer, primary_key=True)
    external_id = Column(Integer, ForeignKey('processes.external_id', ondelete='CASCADE'))
    advogados_adversos = Column(String(500))  # Lista de advogados
    nome_titular = Column(String(200))  # Nome do titular do acordo
    cpf_cnpj_titular = Column(String(20))  # CPF/CNPJ do titular
    valor = Column(String(100))  # Valor do acordo (mantido como string: "R$ 5.500,00")
    data_pagamento = Column(DateTime)  # Data de pagamento
    created_at = Column(DateTime, default=datetime.now)
    
    # Relacionamento
    process = relationship("Process", back_populates="agreements")

class FraudAssessment(Base):
    """Modelo para armazenar avaliações de fraude"""
    __tablename__ = 'fraud_assessments'
    
    id = Column(Integer, primary_key=True)
    external_id = Column(Integer, ForeignKey('processes.external_id', ondelete='CASCADE'))
    process_number = Column(String(255), nullable=False)
    assessment_date = Column(DateTime, nullable=False, default=datetime.utcnow)
    assessment_result = Column(Enum('Pendente', 'Positiva', 'Negativa', 'Falso Positivo', name='assessment_result_enum'), nullable=False, default='Pendente')
    reason_conclusion = Column(Enum('Individuo não Consta nos Autos', 'Falha na Extração', 'Dados Divergentes', 'Individuo Consta nos Autos', name='reason_conclusion_enum'), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relacionamento
    process = relationship("Process", back_populates="fraud_assessments")

    def __repr__(self):
        return f"<FraudAssessment(process_number='{self.process_number}', result='{self.assessment_result}')>"
