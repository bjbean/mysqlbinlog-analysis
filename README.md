# mysqlbinlog-analysis
### 本脚本实现了mysqlbinlog输出结果的解析，生成对应SQL语句或逆向语句。主要目的方便查看mysqlbinlog输出结果，不建议在线上作为数据恢复等工具使用。

### 1.使用条件    
#### 软件环境    
    - mysqldb模块
    - python 2.6以上环境     
#### 数据库环境
    - mysql启用了binlog
    - log模式为row
    - 启用gtid（非必须）
#### 限制情况
    如果日志对象在分析时，发生了DDL变化，则对象名可能无法对应。

### 2.使用说明
    $python mysqlbinlog_analysis.py -h
    option -h requires argument
    Usage:
        ./mysqlbinlog_analysis.py -i <hostname or ip> -u <mysql_user> -p <password> -m <redo|undo> -l <log_file> -o <output_file>
        -i : database ip address/domain name
        -u : mysql database user name
        -p : mysql database user password
        -m : function mode
             redo  - redo sql(time + sqltext)
             redo1 - same as redo
             redo2 - redo sql(time + sqltext + gtid)
             redo3 - redo sql(time + sqltext + gtid + logpos)
             undo  - undo sql
        -l : mysql binlog file(mysqlbinlog xxx -v --base64-output=decode-rows > logfile)
        -d : database name 
        -t : table name 
        -f : output to file (default to screen)
             file name is logfile + function_mode + '.sql'
        -h : help information
#### 参数说明
    -m
      指定工作模式，目前支持四种。原有脚本支持redo、undo，扩展了redo2、redo3模式，提供更丰富的信息。
    -l
      指定输入的日志文件。该文件是通过mysqlbinlog分析后的文件。
    -f
      指定输出的目的，默认是屏幕(不指定此参数即可)。如果指定的话，则生成到文件中，文件名规则为logfile_name+function_mode+“.sql”。
#### 使用示例
    $ mysqlbinlog mysql_bin.000027 -v --base64-output=decode-rows>/tmp/mysqlbinlog.log
    $ python mysqlbinlog_analysis.py -i localhost -u root -p 123456 -m redo1 -l /tmp/mysqlbinlog.log
    $ python mysqlbinlog_analysis.py -i localhost -u root -p 123456 -m redo2 -l /tmp/mysqlbinlog.log
    $ python mysqlbinlog_analysis.py -i localhost -u root -p 123456 -m redo3 -l /tmp/mysqlbinlog.log
    $ python mysqlbinlog_analysis.py -i localhost -u root -p 123456 -m undo -l /tmp/mysqlbinlog.log

### 3.输出说明      
#### REDO模式
    输出为时间和SQL文本。
    #TIME: 2016-12-13 22:44:05
    INSERT INTO `test`.`t_test` values(   1   ,1);
    #TIME: 2016-12-13 22:44:16
    INSERT INTO `test`.`t_test` values(   2   ,2);
    #TIME: 2016-12-13 22:44:34
    UPDATE `test`.`t_test` SET   `a`=2   , `b`=3 WHERE   `a`=2   AND `b`=2 ;
    #TIME: 2016-12-13 22:44:40
    DELETE FROM `test`.`t_test` WHERE   `a`=1   AND `b`=1;    
#### REDO2模式
    在以上模式基础上，增加了GTID信息输出。
    #TIME: 2016-12-13 22:44:05
    #GTID: 3809e73c-701b-11e6-9202-000c29273501:563461
    INSERT INTO `test`.`t_test` values(   1   ,1);
    #TIME: 2016-12-13 22:44:16
    #GTID: 3809e73c-701b-11e6-9202-000c29273501:563462
    INSERT INTO `test`.`t_test` values(   2   ,2);
    #TIME: 2016-12-13 22:44:34
    #GTID: 3809e73c-701b-11e6-9202-000c29273501:563463
    UPDATE `test`.`t_test` SET   `a`=2   , `b`=3 WHERE   `a`=2   AND `b`=2 ;
    #TIME: 2016-12-13 22:44:40
    #GTID: 3809e73c-701b-11e6-9202-000c29273501:563464
    DELETE FROM `test`.`t_test` WHERE   `a`=1   AND `b`=1;
#### REDO3模式
    在以上模式基础上，增加了LOGPOS信息输出。
    #LOGPOS: 259
    use `test`;
    create table t_test(a int ,b int);
    #LOGPOS: 431
    BEGIN;
    #LOGPOS: 553
    #TIME: 2016-12-13 22:44:05
    #GTID: 3809e73c-701b-11e6-9202-000c29273501:563461
    INSERT INTO `test`.`t_test` values(   1   ,1);
    #LOGPOS: 597
    COMMIT;          
#### UNDO模式
    生成上述SQL的逆向SQL
    #TIME: 2016-12-13 22:44:40
    INSERT INTO `test`.`t_test` VALUES (   1   , 1);
    #TIME: 2016-12-13 22:44:34
    UPDATE `test`.`t_test` SET   `a`=2   , `b`=2  WHERE   `a`=2   AND `b`=3;
    #TIME: 2016-12-13 22:44:16
    DELETE FROM `test`.`t_test` WHERE   `a`=2   AND `b`=2;
    #TIME: 2016-12-13 22:44:05
    DELETE FROM `test`.`t_test` WHERE   `a`=1   AND `b`=1;
