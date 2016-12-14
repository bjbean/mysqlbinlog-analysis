# mysqlbinlog-analysis
### 本脚本实现了mysqlbinlog输出结果的解析，生成对应SQL语句或逆向语句。
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
