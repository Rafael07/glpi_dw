from pydantic import BaseModel, Field, field_validator
from typing import Optional
from datetime import datetime

class TicketSchema(BaseModel):
    """Mapeia o retorno real da API SECTIES-PB para o nosso DW."""
    
    id: int = Field(..., alias="2")
    titulo: Optional[str] = Field(default="Sem Título", alias="1")
    status_id: int = Field(..., alias="12")
    data_abertura: datetime = Field(..., alias="15")
    categoria: str = Field(default="Sem categoria", alias="7")
    
    # IDs para futuras dimensões
    requerente_id: Optional[str] = Field(None, alias="4")
    tecnico_id: Optional[str] = Field(None, alias="5")

    class Config:
        populate_by_name = True
        extra = "ignore"

    @field_validator("categoria", mode="before")
    @classmethod
    def trata_categoria_nula(cls, value):
        if not value or value == "null":
            return "Sem categoria"
        return str(value)

    # Novo validador para lidar com chamados que têm mais de 1 técnico/requerente
    @field_validator("requerente_id", "tecnico_id", mode="before")
    @classmethod
    def trata_multiplos_usuarios(cls, value):
        # Se o GLPI mandar uma lista (ex: ['16', '17'])
        if isinstance(value, list):
            # Transforma em uma única string separada por vírgula: "16,17"
            return ",".join(str(v) for v in value)
        
        # Se for None, nulo, etc, mantém como None
        if not value:
            return None
            
        # Se for um valor único, converte pra string e segue a vida
        return str(value)