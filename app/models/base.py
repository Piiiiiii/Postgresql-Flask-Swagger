from contextlib import contextmanager
from datetime import datetime
from flask import current_app, json
from flask_sqlalchemy import SQLAlchemy as _SQLAlchemy, Pagination as _Pagination, BaseQuery
from sqlalchemy import Column, SmallInteger, Integer, orm, inspect

from app.libs.error_code import NotFound
from time import localtime, strftime


class SQLAlchemy(_SQLAlchemy):
    @contextmanager
    def auto_commit(self):
        try:
            yield
            self.session.commit()  # 事务
        except Exception as e:
            self.session.rollback()  # 回滚
            raise e


class Pagination(_Pagination):
    def hide(self, *keys):
        for item in self.items:
            item.hide(*keys)
        return self


class Query(BaseQuery):
    def filter_by(self, **kwargs):
        if 'status' not in kwargs.keys():
            kwargs['status'] = 1
        return super(Query, self).filter_by(**kwargs)

    def get_or_404(self, ident, e=None, error_code=None, msg=None):
        rv = self.get(ident)  # 查询主键
        if not rv:
            if e:
                raise e
            raise NotFound(error_code=error_code, msg=msg)
        return rv

    def first_or_404(self, e=None, error_code=None, msg=None):
        '''
        :param e: 异常(exception)
        :param error_code: 错误码
        :param msg: 错误信息
        :return:
        '''
        rv = self.first()
        if not rv:
            if e:
                raise e
            raise NotFound(error_code=error_code, msg=msg)
        return rv

    def all_or_404(self, e=None, error_code=None, msg=None):
        rv = list(self)
        if not rv:
            if e:
                raise e
            raise NotFound(error_code=error_code, msg=msg)
        return rv

    def all(self):
        rv = list(self)
        if not rv:
            raise NotFound()
        return rv

    def paginate(self, page=None, per_page=None, error_out=True, max_per_page=None):
        # 使用paginator记的加上filter_by，用于默认添加status=1
        paginator = BaseQuery.paginate(
            self, page=page, per_page=per_page, error_out=error_out,
            max_per_page=max_per_page
        )
        return Pagination(
            self,
            paginator.page,
            paginator.per_page,
            paginator.total,
            paginator.items
        )


db = SQLAlchemy(query_class=Query)


class Base(db.Model):
    __abstract__ = True
    create_time = Column('create_time', Integer)
    delete_time = Column(Integer)
    update_time = Column(Integer)
    status = Column(SmallInteger, default=1)  # 软删除

    @orm.reconstructor
    def init_on_load(self):
        # 被隐藏的属性则无法用append方法添加
        self.exclude = ['create_time', 'update_time', 'delete_time', 'status']
        all_columns = inspect(self.__class__).columns.keys()
        self.fields = list(set(all_columns) - set(self.exclude))

    def __init__(self):
        self.create_time = int(datetime.now().timestamp())

    def __getitem__(self, item):
        attr = getattr(self, item)
        # 将字符串转为JSON
        if isinstance(attr, str):
            try:
                attr = json.loads(attr)
            except ValueError:
                pass
        # 处理时间(时间戳转化)
        if item in ['create_time', 'update_time', 'delete_time']:
            attr = strftime('%Y-%m-%d %H:%M:%S', localtime(attr))
        return attr

    @property
    def create_datetime(self):
        if self.create_time:
            return datetime.fromtimestamp(self.create_time)
        else:
            return None

    def get_url(self, url):
        if (self._from == 1):
            return current_app.config['IMG_PREFIX'] + url
        else:
            return url

    def set_attrs(self, **kwargs):
        # 快速赋值
        # 用法: set_attrs(form.data)
        for key, value in kwargs.items():
            if hasattr(self, key) and key != 'id':
                setattr(self, key, value)

    def delete(self):
        self.status = 0

    def keys(self):
        # 在 app/app.py中的 JSONEncoder中的 dict(o)使用
        # 在此处，整合要输出的属性：self.fields
        return self.fields

    def hide(self, *keys):
        for key in keys:
            self.exclude.append(key)
            if key in self.fields:
                self.fields.remove(key)
        return self

    def append(self, *keys):
        for key in keys:
            # self.fields 暂未有key
            # and
            # 在 Model层和 Service层等任意的操作中，已经隐藏的属性无法再添加
            if key not in self.fields and key not in self.exclude:
                self.fields.append(key)
        return self
