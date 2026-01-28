#define PY_SSIZE_T_CLEAN
#include <Python.h>
#include <structmember.h>

typedef struct {
    PyObject_HEAD
    PyObject *vars;  
    PyObject *parent;
} NativeEnvObject;

static PyTypeObject NativeEnvType;

static int
is_env_descendant(PyObject *origin, PyObject *declaring) {
    if (!origin || origin == Py_None || !declaring) return 0;

    PyObject *cur = origin;
    Py_INCREF(cur);
    while (cur && cur != Py_None) {
        int eq = PyObject_RichCompareBool(cur, declaring, Py_EQ);
        if (eq < 0) {
            Py_DECREF(cur);
            PyErr_Clear();
            return 0;
        }
        if (eq == 1) {
            Py_DECREF(cur);
            return 1;
        }
        PyObject *next_parent = PyObject_GetAttrString(cur, "parent");
        Py_DECREF(cur);
        if (!next_parent) {
            PyErr_Clear();
            return 0;
        }
        cur = next_parent;
    }
    Py_XDECREF(cur);
    return 0;
}

static int
NativeEnv_init(NativeEnvObject *self, PyObject *args, PyObject *kwds) {
    static char *kwlist[] = {"parent", NULL};
    PyObject *parent = Py_None;

    if (!PyArg_ParseTupleAndKeywords(args, kwds, "|O", kwlist, &parent))
        return -1;

    Py_INCREF(parent);
    self->parent = parent;

    self->vars = PyDict_New();
    if (!self->vars) {
        Py_DECREF(parent);
        return -1;
    }
    return 0;
}

static void
NativeEnv_dealloc(NativeEnvObject *self) {
    Py_XDECREF(self->vars);
    Py_XDECREF(self->parent);
    Py_TYPE(self)->tp_free((PyObject *) self);
}

static PyObject *
NativeEnv_bind_this(NativeEnvObject *self, PyObject *args) {
    PyObject *this_obj = NULL;
    if (!PyArg_ParseTuple(args, "O", &this_obj))
        return NULL;

    if (!this_obj) {
        PyErr_SetString(PyExc_ValueError, "'this' object cannot be NULL");
        return NULL;
    }

    PyObject *key = PyUnicode_FromString("this");
    if (!key)
        return NULL;

    Py_INCREF(this_obj);
    Py_INCREF(Py_None);
    Py_INCREF(Py_False);
    PyObject *entry = PyTuple_Pack(3, this_obj, Py_None, Py_False);
    if (!entry) {
        Py_DECREF(key);
        Py_DECREF(this_obj);
        Py_DECREF(Py_None);
        Py_DECREF(Py_False);
        return NULL;
    }

    int result = PyDict_SetItem(self->vars, key, entry);

    Py_DECREF(entry);
    Py_DECREF(key);

    if (result < 0) {
        PyErr_SetString(PyExc_RuntimeError, "Failed to set 'this' in environment vars");
        return NULL;
    }

    Py_RETURN_NONE;
}

static PyObject *
NativeEnv_define(NativeEnvObject *self, PyObject *args) {
    const char *name;
    PyObject *value;
    const char *vtype = NULL;
    int is_private = 0;

    if (!PyArg_ParseTuple(args, "sO|sp", &name, &value, &vtype, &is_private))
        return NULL;

    PyObject *v_obj = value;
    Py_INCREF(v_obj);

    PyObject *vtype_obj;
    if (vtype) {
        vtype_obj = PyUnicode_FromString(vtype);
        if (!vtype_obj) {
            Py_DECREF(v_obj);
            return NULL;
        }
    } else {
        vtype_obj = Py_None;
        Py_INCREF(Py_None);
    }

    PyObject *priv_obj = is_private ? Py_True : Py_False;
    Py_INCREF(priv_obj);

    PyObject *entry = PyTuple_Pack(3, v_obj, vtype_obj, priv_obj);
    if (!entry) {
        Py_DECREF(v_obj);
        Py_DECREF(vtype_obj);
        Py_DECREF(priv_obj);
        return NULL;
    }

    int ret = PyDict_SetItemString(self->vars, name, entry);

    Py_DECREF(entry);
    Py_DECREF(v_obj);
    Py_DECREF(vtype_obj);
    Py_DECREF(priv_obj);

    if (ret < 0) return NULL;
    Py_RETURN_NONE;
}

static PyObject *
NativeEnv_get(NativeEnvObject *self, PyObject *args) {
    const char *name;
    PyObject *origin = Py_None;

    if (!PyArg_ParseTuple(args, "s|O", &name, &origin))
        return NULL;

    PyObject *key = PyUnicode_FromString(name);
    if (!key) return NULL;

    PyObject *entry = PyDict_GetItem(self->vars, key);
    if (entry) {
        if (!PyTuple_Check(entry) || PyTuple_Size(entry) != 3) {
            Py_INCREF(entry);
            Py_DECREF(key);
            return entry;
        }

        PyObject *is_priv = PyTuple_GetItem(entry, 2);
        int private_flag = PyObject_IsTrue(is_priv);

        if (private_flag) {
            if (!origin || origin == Py_None) {
                Py_DECREF(key);
                PyErr_Format(PyExc_PermissionError, "AccessError: '%s' is private", name);
                return NULL;
            }
            if (!is_env_descendant(origin, (PyObject *) self)) {
                Py_DECREF(key);
                PyErr_Format(PyExc_PermissionError, "AccessError: '%s' is private", name);
                return NULL;
            }
        }

        Py_INCREF(entry);
        Py_DECREF(key);
        return entry;
    }

    PyObject *parent = self->parent;
    if (parent) Py_INCREF(parent);
    while (parent && parent != Py_None) {
        if (PyObject_TypeCheck(parent, &NativeEnvType)) {
            NativeEnvObject *pobj = (NativeEnvObject *) parent;
            PyObject *pv = PyDict_GetItem(pobj->vars, key);
            if (pv) {
                if (PyTuple_Check(pv) && PyTuple_Size(pv) == 3) {
                    PyObject *is_priv = PyTuple_GetItem(pv, 2);
                    int private_flag = PyObject_IsTrue(is_priv);
                    if (private_flag) {
                        if (!origin || origin == Py_None) {
                            Py_DECREF(parent);
                            Py_DECREF(key);
                            PyErr_Format(PyExc_PermissionError, "AccessError: '%s' is private", name);
                            return NULL;
                        }
                        if (!is_env_descendant(origin, (PyObject *) pobj)) {
                            Py_DECREF(parent);
                            Py_DECREF(key);
                            PyErr_Format(PyExc_PermissionError, "AccessError: '%s' is private", name);
                            return NULL;
                        }
                    }
                    Py_INCREF(pv);
                    Py_DECREF(parent);
                    Py_DECREF(key);
                    return pv;
                } else {
                    Py_INCREF(pv);
                    Py_DECREF(parent);
                    Py_DECREF(key);
                    return pv;
                }
            }
            PyObject *next_parent = pobj->parent;
            if (next_parent) Py_INCREF(next_parent);
            Py_DECREF(parent);
            parent = next_parent;
            continue;
        }

        PyObject *pvars = PyObject_GetAttrString(parent, "vars");
        if (pvars && PyDict_Check(pvars)) {
            PyObject *pv = PyDict_GetItem(pvars, key);
            if (pv) {
                if (PyTuple_Check(pv) && PyTuple_Size(pv) == 3) {
                    PyObject *is_priv = PyTuple_GetItem(pv, 2);
                    int private_flag = PyObject_IsTrue(is_priv);
                    if (private_flag) {
                        if (!origin || origin == Py_None) {
                            Py_DECREF(pvars);
                            Py_DECREF(parent);
                            Py_DECREF(key);
                            PyErr_Format(PyExc_PermissionError, "AccessError: '%s' is private", name);
                            return NULL;
                        }
                        if (!is_env_descendant(origin, parent)) {
                            Py_DECREF(pvars);
                            Py_DECREF(parent);
                            Py_DECREF(key);
                            PyErr_Format(PyExc_PermissionError, "AccessError: '%s' is private", name);
                            return NULL;
                        }
                    }
                    Py_INCREF(pv);
                    Py_DECREF(pvars);
                    Py_DECREF(parent);
                    Py_DECREF(key);
                    return pv;
                } else {
                    Py_INCREF(pv);
                    Py_DECREF(pvars);
                    Py_DECREF(parent);
                    Py_DECREF(key);
                    return pv;
                }
            }
            Py_DECREF(pvars);
        } else {
            Py_XDECREF(pvars);
            PyObject *get_m = PyObject_GetAttrString(parent, "get");
            if (get_m && PyCallable_Check(get_m)) {
                PyObject *res = PyObject_CallFunctionObjArgs(get_m, key, NULL);
                Py_DECREF(get_m);
                if (res) {
                    Py_DECREF(parent);
                    Py_DECREF(key);
                    return res;
                } else {
                    Py_DECREF(parent);
                    Py_DECREF(key);
                    return NULL;
                }
            }
            Py_XDECREF(get_m);
            PyErr_Clear();
        }

        PyObject *next_parent = PyObject_GetAttrString(parent, "parent");
        if (!next_parent) {
            PyErr_Clear();
            Py_DECREF(parent);
            break;
        }
        Py_DECREF(parent);
        parent = next_parent;
    }

    Py_DECREF(key);
    PyErr_Format(PyExc_Exception, "Variable '%s' not defined", name);
    return NULL;
}

static PyObject *
NativeEnv_assign(NativeEnvObject *self, PyObject *args) {
    const char *name;
    PyObject *value;
    if (!PyArg_ParseTuple(args, "sO", &name, &value))
        return NULL;

    PyObject *key = PyUnicode_FromString(name);
    if (!key)
        return NULL;

    PyObject *entry = PyDict_GetItem(self->vars, key);
    if (entry) {
        if (PyTuple_Check(entry) && PyTuple_Size(entry) == 3) {
            PyObject *old_vtype = PyTuple_GetItem(entry, 1);
            PyObject *old_priv = PyTuple_GetItem(entry, 2);

            if (old_vtype != Py_None && PyUnicode_Check(old_vtype)) {
                const char *expected_type_name = PyUnicode_AsUTF8(old_vtype);
                if (!expected_type_name) {
                    Py_DECREF(key);
                    return NULL;
                }

                if (strcmp(expected_type_name, "auto") != 0) {
                    const char *actual_type_name = Py_TYPE(value)->tp_name;
                    if (strcmp(expected_type_name, actual_type_name) != 0) {
                        Py_DECREF(key);
                        PyErr_Format(PyExc_TypeError,
                            "TypeError: cannot assign value of type '%s' to variable '%s' of type '%s'",
                            actual_type_name, name, expected_type_name);
                        return NULL;
                    }
                }
            }

            Py_INCREF(value);
            Py_INCREF(old_vtype);
            Py_INCREF(old_priv);

            PyObject *new_entry = PyTuple_Pack(3, value, old_vtype, old_priv);
            if (!new_entry) {
                Py_DECREF(value);
                Py_DECREF(old_vtype);
                Py_DECREF(old_priv);
                Py_DECREF(key);
                return NULL;
            }

            int res = PyDict_SetItem(self->vars, key, new_entry);
            Py_DECREF(new_entry);
            Py_DECREF(key);

            if (res < 0)
                return NULL;

            Py_RETURN_NONE;
        } else {
            Py_INCREF(value);
            if (PyDict_SetItem(self->vars, key, value) < 0) {
                Py_DECREF(value);
                Py_DECREF(key);
                return NULL;
            }
            Py_DECREF(key);
            Py_RETURN_NONE;
        }
    }

    PyObject *parent = self->parent;
    if (parent && parent != Py_None) {
        if (PyObject_TypeCheck(parent, &NativeEnvType)) {
            NativeEnvObject *pobj = (NativeEnvObject *)parent;
            PyObject *res = PyObject_CallMethod((PyObject *)pobj, "assign", "sO", name, value);
            if (!res) {
                Py_DECREF(key);
                return NULL;
            }
            Py_DECREF(res);
            Py_DECREF(key);
            Py_RETURN_NONE;
        }

        PyObject *res = PyObject_CallMethod(parent, "assign", "sO", name, value);
        if (res) {
            Py_DECREF(res);
            Py_DECREF(key);
            Py_RETURN_NONE;
        }
        PyErr_Clear();

        PyObject *pvars = PyObject_GetAttrString(parent, "vars");
        if (pvars && PyDict_Check(pvars)) {
            PyObject *old = PyDict_GetItem(pvars, key);
            if (old && PyTuple_Check(old) && PyTuple_Size(old) == 3) {
                PyObject *old_vtype = PyTuple_GetItem(old, 1);
                PyObject *old_priv = PyTuple_GetItem(old, 2);

                if (old_vtype != Py_None && PyUnicode_Check(old_vtype)) {
                    const char *expected_type_name = PyUnicode_AsUTF8(old_vtype);
                    if (!expected_type_name) {
                        Py_DECREF(key);
                        Py_DECREF(pvars);
                        return NULL;
                    }

                    if (strcmp(expected_type_name, "auto") != 0) {
                        const char *actual_type_name = Py_TYPE(value)->tp_name;
                        if (strcmp(expected_type_name, actual_type_name) != 0) {
                            Py_DECREF(key);
                            Py_DECREF(pvars);
                            PyErr_Format(PyExc_TypeError,
                                "TypeError: cannot assign value of type '%s' to variable '%s' of type '%s'",
                                actual_type_name, name, expected_type_name);
                            return NULL;
                        }
                    }
                }

                Py_INCREF(value);
                Py_INCREF(old_vtype);
                Py_INCREF(old_priv);

                PyObject *new_entry = PyTuple_Pack(3, value, old_vtype, old_priv);
                if (!new_entry) {
                    Py_DECREF(key);
                    Py_DECREF(pvars);
                    return NULL;
                }

                if (PyDict_SetItem(pvars, key, new_entry) < 0) {
                    Py_DECREF(new_entry);
                    Py_DECREF(key);
                    Py_DECREF(pvars);
                    return NULL;
                }

                Py_DECREF(new_entry);
                Py_DECREF(pvars);
                Py_DECREF(key);
                Py_RETURN_NONE;
            } else {
                Py_INCREF(value);
                if (PyDict_SetItem(pvars, key, value) < 0) {
                    Py_DECREF(value);
                    Py_DECREF(pvars);
                    Py_DECREF(key);
                    return NULL;
                }
                Py_DECREF(pvars);
                Py_DECREF(key);
                Py_RETURN_NONE;
            }
        }
        Py_XDECREF(pvars);
    }

    Py_DECREF(key);
    PyErr_Format(PyExc_Exception, "Variable '%s' not defined", name);
    return NULL;
}

static PyObject *
NativeEnv_has(NativeEnvObject *self, PyObject *args) {
    const char *name;
    if (!PyArg_ParseTuple(args, "s", &name))
        return NULL;

    PyObject *key = PyUnicode_FromString(name);
    if (!key)
        return NULL;

    int contains = PyDict_Contains(self->vars, key);
    if (contains == 1) {
        Py_DECREF(key);
        Py_RETURN_TRUE;
    } else if (contains < 0) {
        Py_DECREF(key);
        return NULL;
    }

    PyObject *parent = self->parent;
    if (parent && parent != Py_None) {
        Py_INCREF(parent);
        while (parent && parent != Py_None) {
            if (PyObject_TypeCheck(parent, &NativeEnvType)) {
                NativeEnvObject *pobj = (NativeEnvObject *) parent;
                int pcontains = PyDict_Contains(pobj->vars, key);
                if (pcontains == 1) {
                    Py_DECREF(parent);
                    Py_DECREF(key);
                    Py_RETURN_TRUE;
                } else if (pcontains < 0) {
                    Py_DECREF(parent);
                    Py_DECREF(key);
                    return NULL;
                }
                PyObject *next_parent = pobj->parent;
                if (next_parent)
                    Py_INCREF(next_parent);
                Py_DECREF(parent);
                parent = next_parent;
            } else {
                Py_DECREF(parent);
                break;
            }
        }
    }

    Py_DECREF(key);
    Py_RETURN_FALSE;
}

static PyObject *
NativeEnv_new_child_env(NativeEnvObject *self, PyObject *Py_UNUSED(ignored)) {
    PyObject *args = PyTuple_Pack(1, (PyObject *)self);
    if (!args)
        return NULL;

    PyObject *kwargs = NULL;

    PyObject *child_env = PyObject_Call((PyObject *)&NativeEnvType, args, kwargs);
    Py_DECREF(args);
    return child_env;
}

static PyMemberDef NativeEnv_members[] = {
    {"parent", T_OBJECT_EX, offsetof(NativeEnvObject, parent), 0, "parent environment"},
    {"vars", T_OBJECT_EX, offsetof(NativeEnvObject, vars), 0, "variables dict"},
    {NULL}
};

static PyMethodDef NativeEnv_methods[] = {
    {"define", (PyCFunction) NativeEnv_define, METH_VARARGS, "Define variable: define(name, value, vtype=None, is_private=False)"},
    {"get", (PyCFunction) NativeEnv_get, METH_VARARGS, "Get variable: get(name, origin_env=None)"},
    {"assign", (PyCFunction) NativeEnv_assign, METH_VARARGS, "Assign variable: assign(name, value)"},
    {"bind_this", (PyCFunction) NativeEnv_bind_this, METH_VARARGS, "Bind 'this' to environment"},
    {"has", (PyCFunction) NativeEnv_has, METH_VARARGS, "Check if variable exists"},
    {"new_child_env", (PyCFunction) NativeEnv_new_child_env, METH_NOARGS, "Create new child environment"},
    {NULL}
};

static PyTypeObject NativeEnvType = {
    PyVarObject_HEAD_INIT(NULL, 0)
    .tp_name = "native_env.Environment",
    .tp_basicsize = sizeof(NativeEnvObject),
    .tp_itemsize = 0,
    .tp_flags = Py_TPFLAGS_DEFAULT,
    .tp_doc = "Native Environment object",
    .tp_methods = NativeEnv_methods,
    .tp_members = NativeEnv_members,
    .tp_init = (initproc) NativeEnv_init,
    .tp_dealloc = (destructor) NativeEnv_dealloc,
    .tp_new = PyType_GenericNew,
};

static PyModuleDef native_env_module = {
    PyModuleDef_HEAD_INIT,
    "native_env",
    "Native Environment module",
    -1,
    NULL, NULL, NULL, NULL, NULL
};

PyMODINIT_FUNC
PyInit_native_env(void) {
    PyObject *m;

    if (PyType_Ready(&NativeEnvType) < 0)
        return NULL;

    m = PyModule_Create(&native_env_module);
    if (!m)
        return NULL;

    Py_INCREF(&NativeEnvType);
    if (PyModule_AddObject(m, "Environment", (PyObject *) &NativeEnvType) < 0) {
        Py_DECREF(&NativeEnvType);
        Py_DECREF(m);
        return NULL;
    }

    return m;
}
