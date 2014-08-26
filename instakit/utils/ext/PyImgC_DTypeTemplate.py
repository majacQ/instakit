#!/usr/bin/env python

import xerox

# //const npy_intp typecode = NPY_%(npytype)s;

template = u'''
struct CImage_NPY_%(npytype)s : public CImage_Type<%(ctype)s> {
    const char structcode[%(structcodelen)s] = { '%(structcode)s', NILCODE };
    const unsigned int structcode_length = %(structcodelen)s;
    const bool native = %(native)s;
    const bool complex = %(complicated)s;
    CImage_NPY_%(npytype)s() {}
};

template <>
struct CImage_Functor<NPY_%(npytype)s> {
    typedef CImage_NPY_%(npytype)s impl;
    typedef std::integral_constant<NPY_TYPES, NPY_%(npytype)s>::value_type value_type;
};

'''

template = u'''
    typedef integral_constant<NPY_TYPES, NPY_%(npytype)s> ENUM_NPY_%(npytype)s;'''

template = u'''
    { NPY_%(npytype)s, ENUM_NPY_%(npytype)s }, '''

# TRAILING TUPLE: (native, complex)

types = [
    ('BOOL', 'bool', ('?',), (True, False)),
    ('BYTE', 'char', ('b',), (True, False)),
    ('HALF', 'npy_half', ('e',), (False, False)),
    
    ('SHORT', 'short', ('h',), (True, False)),
    ('INT', 'int', ('i',), (True, False)),
    ('LONG', 'long', ('l',), (True, False)),
    ('LONGLONG', 'long long', ('q',), (True, False)),
    ('UBYTE', 'unsigned char', ('B',), (True, False)),
    ('USHORT', 'unsigned short', ('H',), (True, False)),
    ('UINT', 'unsigned int', ('I',), (True, False)),
    ('ULONG', 'unsigned long', ('L',), (True, False)),
    ('ULONGLONG', 'unsigned long long', ('Q',), (True, False)),

    #('INT16', 'short', ('h',), (False, False)),
    #('INT32', 'int', ('i', 'l'), (False, False)),
    #('INT32', 'long', ('l',), (False, False)),
    #('INT64', 'long long', ('q',), (False, False)),
    #('UINT16', 'unsigned short', ('H',), (False, False)),
    #('UINT32', 'unsigned int', ('I', 'L'), (False, False)),
    #('UINT32', 'unsigned long', ('L',), (False, False)),
    #('UINT64', 'unsigned long long', ('Q',), (False, False)),

    ('CFLOAT', 'std::complex<float>', ('f',), (False, True)),
    ('CDOUBLE', 'std::complex<double>', ('d',), (False, True)),
    ('FLOAT', 'float', ('f',), (False, False)),
    ('DOUBLE', 'double', ('d',), (False, False)),
    ('CLONGDOUBLE', 'std::complex<long double>', ('g',), (True, False)),
    ('LONGDOUBLE', 'std::complex<long double>', ('g',), (True, True)),
]

out = u""
for typedef in types:
    npytype, ctype, structcode, flagtuple = typedef
    native, complicated = flagtuple
    out += template % dict(
        npytype=npytype, ctype=ctype,
        structcode=u"', '".join(structcode),
        structcodelen=len(structcode)+1,
        native=str(native).lower(),
        complicated=str(complicated).lower())
xerox.copy(out)
