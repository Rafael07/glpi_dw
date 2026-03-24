from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class TicketSchema(BaseModel):
    """Mapeia o retorno real da API SECTIES-PB para o nosso DW."""
    
    id: int = Field(..., alias="2")
    titulo: str = Field(default="Sem Título", alias="1")
    status_id: int = Field(..., alias="12")
    data_abertura: datetime = Field(..., alias="15")
    categoria: str = Field(default="Não Categorizado", alias="7")
    
    # IDs para futuras dimensões
    requerente_id: Optional[str] = Field(None, alias="4")
    tecnico_id: Optional[str] = Field(None, alias="5")

    class Config:
        populate_by_name = True
        extra = "ignore"