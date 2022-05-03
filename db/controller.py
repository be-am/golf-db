from db.connect import init_db 
from db.connect import db_session 
from db.models import *
import time

def show_tables(): 
    queries = db_session.query(Area) 
    entries = [dict(id=q.id, string=q.area_name) for q in queries] 
    print(entries) 

def add_entry(name): 
    t = Area(area_name=name) 
    
    db_session.add(t) 
    db_session.commit() 

def add_course(area_id, name):
    t = Course(area_id, name) 
    
    db_session.add(t) 
    db_session.commit() 

def add_hole(course_id, name):
    t = Hole(course_id, name) 
    
    db_session.add(t) 
    db_session.commit() 


def add_field(area_id, field_name):
    t = Field(area_id, field_name) 
    
    db_session.add(t) 
    db_session.commit() 

def add_state(hole_id, date, state):
    t = State(hole_id, date, state) 
    
    db_session.add(t) 
    db_session.commit() 


def main(): 
    path = "D://Project/UFO/green_eye/dataset/asiana/db"
    area_list = os.listdir(path)

    init_db()
    # model의 구조가 변경 됐을 때 없는 table 생성해줌
    area_id = 1
    field_id = 1
    course_id = 1
    hole_id = 1
    for area in area_list:
        
        
        add_entry(area)
        field_list = os.listdir(os.path.join(path, area))
        print('field_list = ', field_list)

        for field in field_list:
            
            add_field(area_id, field)
            course_list = os.listdir(os.path.join(path, area, field))
            print('course_list = ', course_list)

            for course in course_list:
                
                add_course(field_id, course)
                hole_list = os.listdir(os.path.join(path, area, field, course))
                print('hole_list = ', hole_list)

                for hole in hole_list:
                    add_hole(course_id, hole)
                    date_list = os.listdir(os.path.join(path, area, field, course, hole))
                    print('date_list=', date_list)

                    for date in date_list:
                        date_basepath = os.path.join(path, area, field, course, hole, date)
                        print('hole = ', hole, 'date_basepath = ', date_basepath)
                        file_list = os.listdir(date_basepath)
                        filepath_dict = {}

                        for filename in file_list:
                            if filename.endswith('dbot.png'):
                                filepath_dict['dbot'] = os.path.join(date_basepath, filename)
                            elif filename.endswith('DSM.tif'):
                                filepath_dict['dsm'] = os.path.join(date_basepath, filename)
                            elif filename.endswith('grade.png'):
                                filepath_dict['grass_grade'] = os.path.join(date_basepath, filename)
                            elif filename.endswith('twin.png'):
                                filepath_dict['twin'] = os.path.join(date_basepath, filename)
                            elif filename.endswith('img.png'):
                                filepath_dict['img'] = os.path.join(date_basepath, filename)

                            else:
                                print(f'filename : {filename} is not a file to save in db')

                        add_state(hole_id, date, state=filepath_dict)

                    hole_id +=1
                course_id +=1
            field_id +=1
        area_id +=1

    show_tables()
    db_session.close() 


class bring_data_by_id:
    def __init__(self):
        pass

    def __call__(self, table_name,id = None):
        if table_name=='Area':
            result = self.bring_all_area(id)
        elif table_name=='Field':
            result = self.bring_all_field(id)
        elif table_name=='Course':
            result = self.bring_all_course(id)
        elif table_name=='Hole':
            result = self.bring_all_hole(id)
        elif table_name=='State':
            result = self.bring_all_state(id)
        return result
        
    def bring_all_area(self, area_name=None):
        if area_name == None:
            queries = db_session.query(Area.id, Area.area_name)
        else:
            queries = db_session.query(Area.id).filter_by(area_name = area_name)
        result = queries.all()
        return result

    def bring_all_field(self, area_id = None):
        if area_id == None:
            queries = db_session.query(Field.id, Field.area_id,Field.field_name)
        else:
            queries = db_session.query(Field.id, Field.area_id,Field.field_name).filter_by(area_id = area_id)
        result = queries.all()
        return result


    def bring_all_course(self, field_id = None):
        if field_id == None:
            queries = db_session.query(Course.id,Course.field_id ,Course.course_name)
        else:
            queries = db_session.query(Course.id,Course.field_id ,Course.course_name).filter_by(field_id = field_id)
            # queries = db_session.query(Course.id,Course.field_id ,Course.course_name).filter_by(id = field_id)
        result = queries.all()
        return result
        
    def bring_all_hole(self, course_id = None):
        if course_id == None:
            queries = db_session.query(Hole.id,Hole.course_id ,Hole.hole_name)
        else:
            queries = db_session.query(Hole.id,Hole.course_id ,Hole.hole_name).filter_by(course_id = course_id)
        result = queries.all()
        return result

    def bring_all_state(self, hole_id = None):
        if hole_id == None:
            queries = db_session.query(State.hole_id, State.date, State.state)
        else:
            queries = db_session.query(State.hole_id, State.date, State.state).filter_by(hole_id = hole_id)
        result = queries.all()
        return result


class bring_data_by_name:
    def __init__(self):
        pass

    def bring_data(self, table_name,id = None):
        if table_name=='Area':
            result = self.bring_all_area(id)
        elif table_name=='Field':
            result = self.bring_all_field(id)
        elif table_name=='Course':
            result = self.bring_all_course(id)
        elif table_name=='Hole':
            result = self.bring_all_hole(id)
        elif table_name=='State':
            result = self.bring_all_state(id)
        return result
        

    def bring_all_field(self, field_name = None):
        queries = db_session.query(Field.id).filter_by(field_name = field_name)
        result = queries.all()
        return result


    def bring_all_course(self, field_id, course_name):
        queries = db_session.query(Course.id).filter_by(field_id = field_id, course_name = course_name)
        result = queries.all()
        return result
        
    def bring_all_hole(self, course_id, hole_name):
        queries = db_session.query(Hole.id,Hole.course_id ,Hole.hole_name).filter_by(course_id = course_id, hole_name = hole_name)
        result = queries.all()
        return result

    def bring_all_state(self, hole_id):
        queries = db_session.query(State.date, State.state).filter_by(hole_id = hole_id)
        result = queries.all()
        return result


    def get_item_from_db(self, name_list):

        name_list = name_list[1:]
        funclist = [self.bring_all_field, self.bring_all_course, self.bring_all_hole, self.bring_all_state]

        for idx, (func, name) in enumerate(zip(funclist, name_list)):
            if idx == 0:
                result =func(name)[0][0]
            elif idx == len(funclist)-1:
                result = func(result)
                return result
            else: 
                result = func(result, name)[0][0]

    

if __name__ == "__main__" : 
    main()

    result = bring_data('State', 1)

    print(result)
