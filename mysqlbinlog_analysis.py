# -*- coding: UTF-8 -*-
#!/usr/bin/python
import re, hashlib, time, datetime
import MySQLdb
import sys
import pprint
import getopt

reload(sys)
sys.setdefaultencoding('utf-8')

def mysql_column_list(host,user,password):
    column_dict = {}
    conn = MySQLdb.connect(host, user, password, 'information_schema', charset="utf8");
    query = """
            select TABLE_SCHEMA,TABLE_NAME,COLUMN_NAME,ORDINAL_POSITION 
            from information_schema.COLUMNS 
            where TABLE_SCHEMA not in ('information_schema','performance_schema') 
            order by TABLE_SCHEMA,TABLE_NAME,ORDINAL_POSITION;"""
    cursor = conn.cursor()
    cursor.execute(query)
    numrows = int(cursor.rowcount)
    for i in range(numrows):
        row = cursor.fetchone()
        database = row[0]
        table = row[1]
        column = row[2]
        order = row[3]
        if database in column_dict:
            if table in column_dict[database]:
                column_dict[database][table].update({ order : column })
            else:
                column_dict[database].update( { table : { order : column } })
        else:
            column_dict.update({ database : { table : { order : column } } })
    conn.close()
    return column_dict

def redo_sql(sql_action,column_dict,dbname,tablename,sql):
    dbname = dbname.replace("`",'')
    tablename = tablename.replace("`",'')
    column_num = len(column_dict[dbname][tablename])
    if sql_action == 'INSERT':
        sql = sql.replace("SET",'values(')
        for i in range(int(column_num),0,-1):
            if i == 1:
                sql = sql.replace('@'+str(i)+'=',"")
            else:
                sql = sql.replace('@'+str(i)+'=',",")
        sql = sql + ");"
    if sql_action == 'UPDATE':
        sql_set = sql.split('SET')[1]
        sql_where = sql.split('WHERE')[1].split('SET')[0]
        sql_head = sql.split('WHERE')[0]
        for i in range(int(column_num),0,-1):
            if i == 1:
                sql_set = sql_set.replace('@'+str(i) , "`"+column_dict[dbname][tablename][i]+"`")
                sql_where = sql_where.replace('@'+str(i) , "`"+column_dict[dbname][tablename][i]+"`")
            else:
                sql_set = sql_set.replace('@'+str(i) , ", "+"`"+column_dict[dbname][tablename][i]+"`")
                sql_where = sql_where.replace('@'+str(i) ,"AND " +"`"+column_dict[dbname][tablename][i]+"`")
        sql = sql_head + "SET" + sql_set + " WHERE" + sql_where + ";"
    if sql_action == 'DELETE':
        for i in range(int(column_num),0,-1):
            if i == 1:
                sql = sql.replace('@'+str(i) , "`"+column_dict[dbname][tablename][i]+"`")
            else:
                sql = sql.replace('@'+str(i) , "AND "+"`"+column_dict[dbname][tablename][i]+"`")
        sql = sql + ";"
    return sql

def undo_sql(sql_action,column_dict,dbname,tablename,sql):
    dbname = dbname.replace("`",'')
    tablename = tablename.replace("`",'')
    column_num = len(column_dict[dbname][tablename])
    if sql_action == 'INSERT':
        sql = sql.replace("INSERT",'DELETE')
        sql = sql.replace("INTO","FROM")
        sql = sql.replace("SET","WHERE")
        for i in range(int(column_num),0,-1):
            if i == 1:
                sql = sql.replace('@'+str(i),"`"+column_dict[dbname][tablename][i]+"`")
            else:
                sql = sql.replace('@'+str(i),"AND "+"`"+column_dict[dbname][tablename][i]+"`")
        sql = sql + ";"
    if sql_action == 'UPDATE':
        sql_set = sql.split('SET')[1]
        sql_where = sql.split('WHERE')[1].split('SET')[0]
        sql_head = sql.split('WHERE')[0]
        for i in range(int(column_num),0,-1):
            if i == 1:
                sql_set = sql_set.replace('@'+str(i) , "`"+column_dict[dbname][tablename][i]+"`")
                sql_where = sql_where.replace('@'+str(i) , "`"+column_dict[dbname][tablename][i]+"`")
            else:
                sql_set = sql_set.replace('@'+str(i) , "AND "+"`"+column_dict[dbname][tablename][i]+"`")
                sql_where = sql_where.replace('@'+str(i) ,", " +"`"+column_dict[dbname][tablename][i]+"`")
        sql = sql_head + "SET" + sql_where + " WHERE" + sql_set + ";"
    if sql_action == 'DELETE':
        sql = sql.replace("DELETE","INSERT")
        sql = sql.replace("FROM","INTO")
        sql = sql.replace("WHERE","VALUES (")
        for i in range(int(column_num),0,-1):
            if i == 1:
                sql = sql.replace('@'+str(i)+"=" , "")
            else:
                sql = sql.replace('@'+str(i)+"=" , ", "+"")
        sql = sql + ");"
    return sql

def deal_log(v_source_file,v_target_file,v_mode,column_dict,v_database_name,v_table_name):
    sql_info = []
    log_info = []
    undo_info = []
    sql = ''
    rsize = 1024 * 1024 * 10
    regex_timestamp = re.compile('SET TIMESTAMP')
    regex_sql = re.compile("###")
    regex_commit = re.compile("COMMIT")
    #regex_float = re.compile(r"(\d+\.\d+)")
    regex_table = re.compile("\`.*?\`")
    regex_float = re.compile(r"(\(\d+)\)")
    regex_gtid = re.compile("SET @@SESSION.GTID_NEXT")
    regex_delimiter = re.compile("DELIMITER")
    regex_at = re.compile("^# at \d+")
    regex_text = re.compile("^[^#]\S+")
    log_delimiter = ''
    log_start = ''
    log_text = ''
    p = 0
    stdin_log = open(v_source_file, 'r')
    if v_target_file:
        stdout_log = open(v_target_file, 'a+')

    try:
        while True:
            stdin_log.seek(p, )
            lines = stdin_log.readlines(rsize)
            p = stdin_log.tell()
            if lines:
                for line in lines:
                    if line.strip():
                        try:
                            line = line.encode('utf-8')
                        except:
                            line = line.decode('GB2312', 'ignore').encode('utf-8')

                    if regex_timestamp.match(line):
                        sql_info.append(line.strip())
                        time_stamp = sql_info[0].split('=')[1].split('/')[0]
                        timeArray = time.localtime(int(time_stamp))
                        date_time_raw = time.strftime("%Y-%m-%d %H:%M:%S", timeArray)                        
                    elif regex_sql.match(line):
                        sql = sql + line.strip() 
                    elif regex_gtid.match(line):
                        sql_gtid = line.strip().split("'")[1]
                    elif regex_delimiter.match(line):
                        log_delimiter = line.replace('DELIMITER','').strip()
                    elif regex_at.match(line):
                        if v_mode == 'redo3':
                            if log_start:                                                        
                                log_text = '#LOGPOS: ' + log_start + '\n'
                            for o in log_info:
                                log_text = log_text + o.strip() + '\n'
                            if v_target_file:
                                stdout_log.write(str(log_text))
                            else:
                                print str(log_text) 
                        
                            log_info = []
                            log_start = line.strip().replace('#','').replace('at','').strip()
                    elif regex_commit.match(line): 
                        log_info.append(line.strip().replace(log_delimiter,'').replace('\n','')+';')
                        sql = sql.replace("###",'')
                        sql = regex_float.sub("", sql)
                        sql_sp = sql.split()
                        sql_action = sql_sp[0]
                        table_info = regex_table.findall(sql)
                        dbname = table_info[0]
                        tablename = table_info[1]
                        if v_database_name=='' or v_database_name==dbname.replace('`',''):
                            if v_table_name=='' or v_table_name==tablename.replace('`',''):
                                if v_mode[:4] == "redo":
                                    sql_redo = redo_sql(sql_action,column_dict,dbname,tablename,sql).lstrip()
                                    if v_mode in ('redo','redo1'):
                                        ext_text = "#TIME: " +  date_time_raw 
                                    elif v_mode in ('redo2','redo3'):
                                        ext_text = "#TIME: " +  date_time_raw + "\n#GTID: " + sql_gtid 

                                    if v_target_file:
                                        stdout_log.write(ext_text + str(sql_redo) + '\n')
                                    else:
                                        print ext_text
                                        print "\033[1;31;40m%s\033[0m" % str(sql_redo) + '\n'
                                elif v_mode == "undo":
                                    sql_undo = undo_sql(sql_action,column_dict,dbname,tablename,sql).lstrip()
                                    ext_text = "#TIME: " +  date_time_raw 
                                    undo_info.append(ext_text+'^&'+sql_undo)
                                sql = ''
                                sql_info =  []
                    elif regex_text.match(line):
                        if line.strip().replace(log_delimiter,'').replace('\n','')<>'':
                            log_info.append(line.strip().replace(log_delimiter,'').replace('\n','')+';')
                    else:
                        pass
                if v_mode == 'redo3':
                    if log_start:                                                        
                        log_text = '#LOGPOS: ' + log_start +'\n'
                    for o in log_info:
                        log_text = log_text + o.strip() + '\n'
                    if v_target_file:
                        stdout_log.write(str(log_text))
                    else:
                        print str(log_text) 
                                    
            if not lines:
                break
        if v_mode == 'undo':
            undo_info.reverse()
            for o in undo_info:
                if v_target_file:
                    stdout_log.write(o.split('^&')[0]+'\n'+ o.split('^&')[1] + '\n')
                else:
                    print o.split('^&')[0]
                    print "\033[1;31;40m%s\033[0m" % o.split('^&')[1]
    finally:
        stdin_log.close()
        if v_target_file:
            stdout_log.close()

def print_help():
    print "Usage:"
    print "    ./mysqlbinlog_analysis.py -i <hostname or ip> -u <mysql_user> -p <password> -m <redo|undo> -l <log_file> -o <output_file>"
    print "    -i : database ip address/domain name"
    print "    -u : mysql database user name"
    print "    -p : mysql database user password"
    print "    -m : function mode"
    print "         redo  - redo sql(time + sqltext)"
    print "         redo1 - same as redo"
    print "         redo2 - redo sql(time + sqltext + gtid)"
    print "         redo3 - redo sql(time + sqltext + gtid + logpos)"
    print "         undo  - undo sql"
    print "    -l : mysql binlog file(mysqlbinlog xxx -v --base64-output=decode-rows > logfile)"
    print "    -d : database name "
    print "    -t : table name "
    print "    -f : output to file (default to screen)"
    print "         file name is logfile + function_mode + '.sql'"
    print "    -h : help information"

if __name__ == "__main__":

    v_db_host = ''
    v_db_user = ''
    v_db_pwd = ''
    v_mode = ''
    v_source_file = ''
    v_target_file = ''
    v_table_name = ''
    v_database_name = ''

    # deal input parameter
    try:
        opts, args = getopt.getopt(sys.argv[1:], "i:h:u:p:m:l:fd:t:")

        for o,v in opts:
            if o == "-i":
                v_db_host = v
            elif o == "-u":
                v_db_user = v
            elif o == "-p":
                v_db_pwd = v
            elif o == "-m":
                v_mode = v.lower()
            elif o == "-l":
                v_source_file = v
            elif o == "-f":
                v_target_file = v_source_file+'.'+v_mode+'.sql'
            elif o == "-t":
                v_table_name = v
            elif o == "-d":
                v_database_name = v

    except getopt.GetoptError,msg:
        print msg
        print_help()
        exit()    

    # initial dict
    v_column_dict = mysql_column_list(v_db_host,v_db_user,v_db_pwd)

    deal_log(v_source_file,v_target_file,v_mode,v_column_dict,v_database_name,v_table_name)

