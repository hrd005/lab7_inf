import re
from itertools import chain

import shedule_pb2

def sequence(*funcs):
    if len(funcs) == 0:
        def result(src):
            yield (), src
        return result
    
    def result(src):
        for arg1, src in funcs[0](src):
            for others, src in sequence(*funcs[1:])(src):
                yield (arg1, ) + others, src
    return result

number_regex = re.compile(r'(-?(?:0|[1-9]\d*)(?:\.\d+)?(?:[eE][+-]?\d+)?)\s*(.*)', re.DOTALL)
def parse_number(src):
    match = number_regex.match(src)
    if match is not None:
        number, src = match.groups()
        yield eval(number), src
        
string_regex = re.compile(r'("(?:[^\\"]|\\["\\/bfnrt]|\\u[0-9a-fA-F]{4})*?")\s*(.*)', re.DOTALL)
def parse_string(src):
    match = string_regex.match(src)
    if match is not None:
        string, src = match.groups()
        yield eval(string), src
        
def parse_word(word, value=None):
    def result(src):
        if src.startswith(word):
            yield value, src[len(word):].lstrip()
    
    result.__name__ = "parse_%s" % word
    return result
    
parse_true = parse_word("true", True)
parse_false = parse_word("false", False)
parse_null = parse_word("null", None)

def parse_value(src):
    for match in chain(
        parse_string(src),
        parse_number(src),
        parse_array(src),
        parse_object(src),
        parse_true(src),
        parse_false(src),
        parse_null(src),
    ):
        yield match
        return

parse_left_square_bracket = parse_word("[")
parse_right_square_bracket = parse_word("]")
parse_empty_array = sequence(parse_left_square_bracket, parse_right_square_bracket)

def parse_array(src):
    for _, src in parse_empty_array(src):
        yield [], src
        return
    
    for (_, items, _), src in sequence(
        parse_left_square_bracket,
        parse_comma_separated_values,
        parse_right_square_bracket,
    )(src):
        yield items, src
    
parse_comma = parse_word(',')
def parse_comma_separated_values(src):
    for (value, _, values), src in sequence(
        parse_value,
        parse_comma,
        parse_comma_separated_values
    )(src):
        yield [value] + values, src
        return
    
    for value, src in parse_value(src):
        yield [value], src

parse_left_curly_bracket = parse_word("{")
parse_right_curly_bracket = parse_word("}")
parse_colon = parse_word(":")
parse_empty_object = sequence(parse_left_curly_bracket, parse_right_curly_bracket)

def parse_object(src):
    for _, src in parse_empty_object(src):
        yield {}, src
        return
    for (_, items, _), src in sequence(
        parse_left_curly_bracket,
        parse_comma_separated_keyvalues,
        parse_right_curly_bracket,
    )(src):
        yield items, src

def parse_keyvalue(src):
    for (key, _, value), src in sequence(
        parse_string,
        parse_colon,
        parse_value
    )(src):
        yield {key: value}, src
        
def parse_comma_separated_keyvalues(src):
    for (keyvalue, _, keyvalues), src in sequence(
        parse_keyvalue,
        parse_comma,
        parse_comma_separated_keyvalues
    )(src):
        keyvalue.update(keyvalues)
        yield keyvalue, src
        return
    
    for keyvalue, src in parse_keyvalue(src):
        yield keyvalue, src

def parse(s):
    s = s.strip()
    match = list(parse_value(s))
    if len(match) != 1:
        raise ValueError("Not a valid JSON file")
    result, src = match[0]
    if src.strip():
        raise ValueError("Not a valid JSON file")
    return result
    
file_i = open("shedule.json", "r", encoding='UTF-8')
s = file_i.read()
r = parse(s)
print(r)

day = shedule_pb2.Day()
day.name = r["day"]
for i in range(len(r["classes"])):
    class1 = day.classes.add()
    #class1.position = shedule_pb2.Day.Class.Position()
    class1.position.time = r["classes"][i]["position"]["time"]
    class1.position.week = shedule_pb2.Day.Class.Week.EVEN if r["classes"][i]["position"]["week"] == "четная неделя" else shedule_pb2.Day.Class.Week.ODD
    #class1.place = shedule_pb2.Day.Class.Place()
    class1.place.auditory = str(r["classes"][i]["place"]["auditory"])
    class1.place.address = r["classes"][i]["place"]["address"]
    #class1._class = shedule_pb2.Day.Class.ClassDescription()
    class1._class.subject = r["classes"][i]["class"]["subject"]
    if r["classes"][i]["class"]["type"] == "ЛЕК":
        class1._class.type = shedule_pb2.Day.Class.ClassType.LECTION
    elif r["classes"][i]["class"]["type"] == "ЛАБ":
        class1._class.type = shedule_pb2.Day.Class.ClassType.LABORATORY
    else:
        class1._class.type = shedule_pb2.Day.Class.ClassType.PRACTICAL
    class1._class.lector = r["classes"][i]["class"]["lector"]
    class1.format = r["classes"][i]["format"]

shedule = shedule_pb2.Shedule()
shedule.days.append(day)

print(shedule)

file_o = open("shedule.bin", "wb")
file_o.write(shedule.SerializeToString())
file_o.close()
