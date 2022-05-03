from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker,scoped_session
from db import config


engine = create_engine(config.DB_URL)
db_session = scoped_session(sessionmaker(autocommit=False, autoflush=False, bind=engine))
#웹에서 주로 사용되지만 일단 넣어줌 

Base = declarative_base()
Base.query = db_session.query_property()

def init_db():
    from db import models
    Base.metadata.create_all(engine)
    #metadata를 통해 engine 으로 연결된 데이터베아스의 테이블을 생성해줌
    
