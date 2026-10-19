from itertools import chain
from dataclasses import dataclass

from keras import layers
import dearpygui.dearpygui as dpg

from Src.Enums import Themes
from Src.Nodes import AbstractNode


@dataclass
class LayerResult:
    layer: layers.Layer
    inputs: set[layers.InputLayer]


class LayerNode(AbstractNode):
    '''
    Класс хранящий данные, для связи нода с слоём нейроной сети.
    '''
    theme_name: Themes = Themes.LAYER
    inputs: set["LayerNode"]
    OUTPUT: LayerResult


    @staticmethod
    def layer(layer: layers.Layer):
        '''
        Фабрика функций, для новых INPUT \ OUTPUT,
        чтоб INPUT мог приходить как args
        '''
        return lambda *args, **kwargs: LayerNode.compile_layer(layer, *args, **kwargs)
    

    @staticmethod
    def compile_layer(layer: layers.Layer, *args: LayerResult, **kwargs):
        '''
        Компанует выход который должен быть у Layer,
        чтоб не городить костыли с обработкой inputs
        '''
        inputs = [arg.layer for arg in args]
        if len(inputs) > 1: inputs = [inputs]

        return LayerResult(layer=layer(**kwargs)(*inputs), 
                            inputs=set().union(*[arg.inputs for arg in args]))
