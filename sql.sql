USE eastmoney_db;
CREATE TABLE IF NOT EXISTS etf_option_data (
                                               id INT PRIMARY KEY AUTO_INCREMENT COMMENT '主键ID，自增唯一标识',
                                               contract_code VARCHAR(20) NOT NULL COMMENT '期权合约代码，对应接口f12字段，页面表头「代码」',
                                               contract_name VARCHAR(50) NOT NULL COMMENT '期权合约名称，对应接口f14字段，页面表头「名称」',
                                               latest_price DECIMAL(10,3) COMMENT '最新价，对应接口f2字段÷1000，页面表头「最新价」',
                                               price_change DECIMAL(10,3) COMMENT '涨跌额，对应接口f4字段÷1000，页面表头「涨跌额」',
                                               price_change_rate DECIMAL(10,2) COMMENT '涨跌幅，对应接口f3字段÷100，页面表头「涨跌幅」',
                                               volume INT COMMENT '成交量（手），对应接口f5字段，页面表头「成交量」',
                                               turnover DECIMAL(15,2) COMMENT '成交额（元），对应接口f6字段，页面表头「成交额」',
                                               position_volume INT COMMENT '持仓量（手），对应接口f108字段，页面表头「持仓量」',
                                               strike_price DECIMAL(10,3) COMMENT '行权价，对应接口f161字段÷1000，页面表头「行权价」',
                                               remain_days INT COMMENT '剩余天数，对应接口f162字段，页面表头「剩余日」',
                                               position_change INT COMMENT '持仓量日增减，对应接口f163字段，页面表头「日增」',
                                               settlement_price_yesterday DECIMAL(10,3) COMMENT '昨日结算价，对应接口f28字段÷1000，页面表头「昨结」',
                                               open_price_today DECIMAL(10,3) COMMENT '今日开盘价，对应接口f17字段÷1000，页面表头「今开」',
                                               etf_type VARCHAR(10) NOT NULL COMMENT 'ETF类型标识，取值50ETF/30ETF，区分不同标的',
                                               create_time DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '数据抓取时间，记录数据入库时间'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='50ETF期权合约数据表，存储东方财富接口抓取的全量期权数据';