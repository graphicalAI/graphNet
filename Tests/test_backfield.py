import unittest

from Src.Utils import Backfield



class test_backfield(unittest.TestCase):

    def test_Backfield(self):

        class A:
            flag = False
            b = Backfield(0)


        a = A()
        A.b.bind(a, lambda _: setattr(a, 'flag', True))
        a.b = 1

        assert a.flag == True
        assert a.b == 1


    def test_Backfield_without_callback(self):

        class A:
            b = Backfield()


        a = A()
        assert a.b is None
        a.b = 5
        assert a.b == 5


    def test_Backfield_default(self):

        class A:
            b = Backfield(7)


        assert A().b == 7
