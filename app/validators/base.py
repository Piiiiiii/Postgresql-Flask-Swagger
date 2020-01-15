from flask import request, _request_ctx_stack
from wtforms import Form, ValidationError

from app.libs.error_code import ParameterException


class BaseValidator(Form):
    def __init__(self):
        data = request.get_json(silent=True)  # body中
        view_args = _request_ctx_stack.top.request.view_args  # 获取view中(path路径里)的args
        args = dict(request.args.to_dict(), **view_args)  # query中: request.args.to_dict()
        super(BaseValidator, self).__init__(data=data, **args)

    def validate_for_api(self):
        valid = super(BaseValidator, self).validate()
        if not valid:
            raise ParameterException(msg=self.errors)
        return self

    def isPositiveInteger(self, value):
        try:
            value = int(value)
        except ValueError:
            return False
        return True if (isinstance(value, int) and value > 0) else False

    def isList(self, value):
        return True if isinstance(value, list) else False
