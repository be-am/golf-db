import sqlalchemy
from sqlalchemy import Enum, ForeignKey, MetaData
from sqlalchemy import Column, Integer, String
from sqlalchemy.types import TypeDecorator
from db.connect import Base
import os
import json

metadata = MetaData()


    
class Area(Base):
    __tablename__ = 'Areas'
    
    metadata,
    id = Column(Integer, primary_key=True, nullable=False)
    area_name = Column(String(50))
    
    def __init__(self, area_name):
        self.area_name = area_name
    


class Field(Base):
    __tablename__ = 'Fields'
    
    id = Column(Integer, primary_key=True, nullable=False)
    field_name = Column(String(50))
    area_id = Column(Integer, ForeignKey(Area.id))
    
    def __init__(self, area_id, field_name):
        self.area_id = area_id
        self.field_name = field_name


class Course(Base):
    __tablename__ = 'Courses'
    
    id = Column(Integer, primary_key=True, nullable=False)
    course_name = Column(String(50))
    field_id = Column(Integer, ForeignKey(Field.id))
    
    def __init__(self, field_id, course_name):
        self.field_id = field_id
        self.course_name = course_name
        
class Hole(Base):
    __tablename__ = 'Holes'
    
    id = Column(Integer, primary_key=True, nullable=False)
    hole_name = Column(String(50))    
    course_id = Column(Integer,ForeignKey(Course.id))

    def __init__(self, course_id, hole_name):
        self.course_id = course_id
        self.hole_name = hole_name


# class State(Base):
#     __tablename__ = 'States'
    
#     id = Column(Integer, primary_key=True, nullable=False)
#     hole_id = Column(Integer,ForeignKey(Hole.id))
#     date = Column(String(50))
#     race_enums = ('img', 'dbot','dsm','grass_grade','twin')
#     state = Column('state',Enum(*race_enums))

#     def __init__(self, hole_id, date, state):
        
#         self.date = date
#         self.hole_id = hole_id
#         self.state = state

class TextPickleType(TypeDecorator):

    impl = sqlalchemy.Text(256)

    def process_bind_param(self, value, dialect):
        if value is not None:
            value = json.dumps(value)

        return value

    def process_result_value(self, value, dialect):
        if value is not None:
            value = json.loads(value)
        return value

class State(Base):
    __tablename__ = 'States'
    id = Column(Integer, primary_key=True, nullable=False)
    hole_id = Column(Integer,ForeignKey(Hole.id))
    date = Column(String(50))
    state = Column(TextPickleType())

    def __init__(self, hole_id, date, state):
        
        self.date = date
        self.hole_id = hole_id
        self.state = state




# Session = sessionmaker(bind=engine)
# session = Session()