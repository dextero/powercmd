import powercmd

class CustomClassWithStringCtor:
    def __init__(self, text):
        self.text = text

    def __str__(self):
        return "I'm a %s(%s)!" % (type(self).__name__, self.text)

class CustomClassWithPowercmdParse:
    @staticmethod
    def powercmd_parse(text):
        return CustomClassWithPowercmdParse(text, caller='powercmd_parse')

    def __init__(self, text, caller='user'):
        self.text = text
        self.caller = caller

    def __str__(self):
        return "I'm a %s(%s), created by %s!" % (type(self).__name__, self.text, self.caller)

class SimpleCmd(powercmd.Cmd):
    # Methods starting with 'do_' are considered command handlers, just like in
    # the standard `cmd` module.
    # Annotating a command handler argument with a type will cause the input to
    # be parsed before passing it to the handler.
    def do_sum(self,
               first: int,
               second: int):
        print('%d + %d = %d' % (first, second, first + second))

    # A custom type can be used if it has a powercmd_parse static method that
    # converts a string into appropriate type or if its constructor can be
    # called with a single string argument.
    def do_print_custom(self,
                        custom: CustomClassWithStringCtor,
                        custom2: CustomClassWithPowercmdParse):
        print(custom)
        print(custom2)

if __name__ == '__main__':
    SimpleCmd().cmdloop()
