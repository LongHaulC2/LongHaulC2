from dataclasses import dataclass
from typing import Optional
from datetime import time
from sqlalchemy import exc
from ..db.mysql_models import Implant


'''
Using dataclasses here for easier creation of correct data input to these functions below,
and it's easier to update for future fields. 

'''
@dataclass
class ImplantCreate:
    external_ip: Optional[str] = None
    internal_ip: Optional[str] = None
    listener: Optional[str] = None
    user: Optional[str] = None
    system_hostname: Optional[str] = None
    notes: Optional[str] = None
    process: Optional[str] = None
    pid: Optional[int] = None
    arch: Optional[str] = None
    last_checkin: Optional[time] = None
    sleep_value: Optional[int] = None

@dataclass
class ImplantUpdate:
    external_ip: Optional[str] = None
    internal_ip: Optional[str] = None
    listener: Optional[str] = None
    user: Optional[str] = None
    system_hostname: Optional[str] = None
    notes: Optional[str] = None
    process: Optional[str] = None
    pid: Optional[int] = None
    arch: Optional[str] = None
    last_checkin: Optional[time] = None
    sleep_value: Optional[int] = None

class ImplantService:
    def __init__(self, session):
        self.session = session

    def create(self, data:ImplantCreate) -> Implant:
        """
        Create a new implant entry.
        """
        try:
            implant = Implant(**vars(data))
            self.session.add(implant)
            self.session.commit()
            self.session.refresh(implant)
            return implant

        except exc.SQLAlchemyError:
            self.session.rollback()
            raise

    def get_by_id(self, implant_id: int) -> Implant | None:
        """
        Retrieve an implant by primary key.
        """
        return self.session.query(Implant).get(implant_id)

    def update(self, implant_id: int, data: ImplantUpdate) -> Implant | None:
        """
        Update an implant by primary key.
        """
        try:
            implant = self.get_by_id(implant_id)
            if not implant:
                return None

            # if value is not supplied, DO NOT update it in DB. 
            # or, only apply supplied values
            for field, value in vars(data).items():
                if value is not None:
                    setattr(implant, field, value)

            self.session.commit()
            return implant
        except SQLAlchemyError:
            self.session.rollback()
            raise

    def delete(self, implant_id: int) -> bool:
        """
        Delete an implant by primary key.
        """
        try:
            implant = self.get_by_id(implant_id)
            if not implant:
                return False

            self.session.delete(implant)
            self.session.commit()
            return True
        except SQLAlchemyError:
            self.session.rollback()
            raise
