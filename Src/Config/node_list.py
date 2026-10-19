import numpy as np

from keras import layers
import keras

from Src.Enums import *
from Src.Nodes import *
from Src.Config.parameter import Parameter
from Src.Config.node_annotation import NodeAnnotation
from Src.Config.Annotations import *


# TODO Сделать сериализацию в JSON?
node_list = {
    "Data & Preprocessing":
    {
        "Import data": [
            NodeAnnotation(
                label = "Tables data",
                node_type = ShapeNode,
                logic = ShapeNode.open_table_data,
                annotations = {
                        "files": Parameter(AttrType.INPUT, AString),
                        "delimiter": Parameter(AttrType.INPUT, AEnum[Delimiters]),
                        "skip_header": Parameter(AttrType.INPUT, ABoolean),
                        "skip_footer": Parameter(AttrType.INPUT, ABoolean),
                        "shape": Parameter(AttrType.OUTPUT, 
                                           ASequence[AInteger, AInteger, AInteger],
                                           backfield=ShapeNode.shape)  
                    },
                input=False,
                output=DataNode
            ),
            NodeAnnotation(
                label="Images data",
                node_type= ShapeNode,
                logic = ShapeNode.open_image_data,
                annotations = {
                        "files": Parameter(AttrType.INPUT, AString),
                        "color_mode": Parameter(AttrType.INPUT, AEnum[ColorMode]),
                        "shape": Parameter(AttrType.OUTPUT, ASequence[AInteger, AInteger, AInteger],
                                           backfield=ShapeNode.shape)
                        },
                input=False,
                output=DataNode
            ),
            NodeAnnotation(
                label="Load Dataset",
                node_type= DatasetNode,
                logic = DatasetNode.open_data,
                annotations = {
                        "dataset": Parameter(AttrType.INPUT, AEnum[Datasets]),
                        "X_train": Parameter(AttrType.OUTPUT, ANode[DataNode]),
                        "y_train": Parameter(AttrType.OUTPUT, ANode[DataNode]),
                        "X_test": Parameter(AttrType.OUTPUT, ANode[DataNode]),
                        "y_test": Parameter(AttrType.OUTPUT, ANode[DataNode]),
                        "shape": Parameter(AttrType.OUTPUT, ASequence[AInteger, AInteger, AInteger],
                                           backfield=DatasetNode.shape)
                        },
                input=False,
                output=False
            ),
        ],
        "Processing Utils": [
            NodeAnnotation(
                label="to categorical",
                node_type= DataNode,
                logic = keras.utils.to_categorical,
                annotations = {
                        "num_classes": Parameter(AttrType.INPUT, AInteger)
                    },
                input=Single[DataNode]
            ),
            NodeAnnotation(
                label="from categorical",
                node_type= DataNode,
                logic = lambda x: np.argmax(x, axis=-1).reshape(-1, 1),
                annotations = {},
                input=Single[DataNode]
            ),
        ]
    },
    "Neural Network Layers":
    {
        "Full":
        [
            NodeAnnotation(
                label= "Dense",
                node_type= LayerNode,
                logic = LayerNode.layer(layers.Dense),
                annotations = {
                        "units": Parameter(AttrType.INPUT, AInteger, default=1),
                        "activation": Parameter(AttrType.INPUT, AEnum[Activations]),
                        "use_bias": Parameter(AttrType.INPUT, ABoolean)
                    },
                input=LayerNode
            ),
            NodeAnnotation(
                label= "Activation",
                node_type= LayerNode,
                logic = LayerNode.layer(layers.Activation),
                annotations = {
                        "activation": Parameter(AttrType.INPUT, AEnum[Activations]),
                    },
                input=LayerNode
            ),
            NodeAnnotation(
                label= "Dropout",
                node_type= LayerNode,
                logic = LayerNode.layer(layers.Dropout),
                annotations = {
                        "rate": Parameter(AttrType.INPUT, AFloat, default=0.2),
                    },
                input=LayerNode
            ),
            NodeAnnotation(
                label= "BatchNormalization",
                node_type= LayerNode,
                logic = LayerNode.layer(layers.BatchNormalization),
                annotations = {},
                input=LayerNode
            ),
            NodeAnnotation(
                label= "LayerNormalization",
                node_type= LayerNode,
                logic = LayerNode.layer(layers.LayerNormalization),
                annotations = {},
                input=LayerNode
            ),
        ],
        "Convolutional":
        [
            NodeAnnotation(
                label= "Conv1D",
                node_type= LayerNode,
                logic = LayerNode.layer(layers.Conv1D),
                annotations = {
                        "filters": Parameter(AttrType.INPUT, AInteger, default=1),
                        "kernel_size": Parameter(AttrType.INPUT, AInteger, default=1),
                        "strides": Parameter(AttrType.INPUT, AInteger, default=1),
                        "padding": Parameter(AttrType.INPUT, AEnum[Padding]),
                        "activation": Parameter(AttrType.INPUT, AEnum[Activations]),
                        "use_bias": Parameter(AttrType.INPUT, ABoolean),
                    },
                input=LayerNode
            ),
            NodeAnnotation(
                label= "Conv2D",
                node_type= LayerNode,
                logic = LayerNode.layer(layers.Conv2D),
                annotations = {
                        "filters": Parameter(AttrType.INPUT, AInteger, default=1),
                        "kernel_size": Parameter(AttrType.INPUT, AInteger, default=1),
                        "strides": Parameter(AttrType.INPUT, AInteger, default=1),
                        "padding": Parameter(AttrType.INPUT, AEnum[Padding]),
                        "activation": Parameter(AttrType.INPUT, AEnum[Activations]),
                        "use_bias": Parameter(AttrType.INPUT, ABoolean),
                    },
                input=LayerNode
            ),
            NodeAnnotation(
                label= "Conv3D",
                node_type= LayerNode,
                logic = LayerNode.layer(layers.Conv3D),
                annotations = {
                        "filters": Parameter(AttrType.INPUT, AInteger, default=1),
                        "kernel_size": Parameter(AttrType.INPUT, AInteger, default=1),
                        "strides": Parameter(AttrType.INPUT, AInteger, default=1),
                        "padding": Parameter(AttrType.INPUT, AEnum[Padding]),
                        "activation": Parameter(AttrType.INPUT, AEnum[Activations]),
                        "use_bias": Parameter(AttrType.INPUT, ABoolean),
                    },
                input=LayerNode
            ),
            NodeAnnotation(
                label= "DepthwiseConv1D",
                node_type= LayerNode,
                logic = LayerNode.layer(layers.DepthwiseConv1D),
                annotations = {
                        "kernel_size": Parameter(AttrType.INPUT, AInteger, default=1),
                        "strides": Parameter(AttrType.INPUT, AInteger, default=1),
                        "depth_multiplier": Parameter(AttrType.INPUT, AInteger, default=1),
                        "padding": Parameter(AttrType.INPUT, AEnum[Padding]),
                        "activation": Parameter(AttrType.INPUT, AEnum[Activations]),
                        "use_bias": Parameter(AttrType.INPUT, ABoolean),
                    },
                input=LayerNode
            ),
            NodeAnnotation(
                label= "DepthwiseConv2D",
                node_type= LayerNode,
                logic = LayerNode.layer(layers.DepthwiseConv2D),
                annotations = {
                        "kernel_size": Parameter(AttrType.INPUT, AInteger, default=1),
                        "strides": Parameter(AttrType.INPUT, AInteger, default=1),
                        "depth_multiplier": Parameter(AttrType.INPUT, AInteger, default=1),
                        "padding": Parameter(AttrType.INPUT, AEnum[Padding]),
                        "activation": Parameter(AttrType.INPUT, AEnum[Activations]),
                        "use_bias": Parameter(AttrType.INPUT, ABoolean),
                    },
                input=LayerNode
            ),
            NodeAnnotation(
                label= "SeparableConv1D",
                node_type= LayerNode,
                logic = LayerNode.layer(layers.SeparableConv1D),
                annotations = {
                        "filters": Parameter(AttrType.INPUT, AInteger, default=1),
                        "kernel_size": Parameter(AttrType.INPUT, AInteger, default=1),
                        "strides": Parameter(AttrType.INPUT, AInteger, default=1),
                        "depth_multiplier": Parameter(AttrType.INPUT, AInteger, default=1),
                        "padding": Parameter(AttrType.INPUT, AEnum[Padding]),
                        "activation": Parameter(AttrType.INPUT, AEnum[Activations]),
                        "use_bias": Parameter(AttrType.INPUT, ABoolean),
                    },
                input=LayerNode
            ),
            NodeAnnotation(
                label= "SeparableConv2D",
                node_type= LayerNode,
                logic = LayerNode.layer(layers.SeparableConv2D),
                annotations = {
                        "filters": Parameter(AttrType.INPUT, AInteger, default=1),
                        "kernel_size": Parameter(AttrType.INPUT, AInteger, default=1),
                        "strides": Parameter(AttrType.INPUT, AInteger, default=1),
                        "depth_multiplier": Parameter(AttrType.INPUT, AInteger, default=1),
                        "padding": Parameter(AttrType.INPUT, AEnum[Padding]),
                        "activation": Parameter(AttrType.INPUT, AEnum[Activations]),
                        "use_bias": Parameter(AttrType.INPUT, ABoolean),
                    },
                input=LayerNode
            ),
            NodeAnnotation(
                label= "MaxPooling1D",
                node_type= LayerNode,
                logic = LayerNode.layer(layers.MaxPooling1D),
                annotations = {
                        "pool_size": Parameter(AttrType.INPUT, AInteger, default=2),
                        "strides": Parameter(AttrType.INPUT, AInteger, default=2),
                        "padding": Parameter(AttrType.INPUT, AEnum[Padding]),
                    },
                input=LayerNode
            ),
            NodeAnnotation(
                label= "MaxPooling2D",
                node_type= LayerNode,
                logic = LayerNode.layer(layers.MaxPooling2D),
                annotations = {
                        "pool_size": Parameter(AttrType.INPUT, ASequence[AInteger, AInteger], default=(2,2)),
                        "strides": Parameter(AttrType.INPUT, ASequence[AInteger, AInteger], default=(2,2)),
                        "padding": Parameter(AttrType.INPUT, AEnum[Padding]),
                    },
                input=LayerNode
            ),
            NodeAnnotation(
                label= "MaxPooling3D",
                node_type= LayerNode,
                logic = LayerNode.layer(layers.MaxPooling3D),
                annotations = {
                        "pool_size": Parameter(AttrType.INPUT, ASequence[AInteger, AInteger, AInteger], default=(2,2,2)),
                        "strides": Parameter(AttrType.INPUT, ASequence[AInteger, AInteger, AInteger], default=(2,2,2)),
                        "padding": Parameter(AttrType.INPUT, AEnum[Padding]),
                    },
                input=LayerNode
            ),
            NodeAnnotation(
                label= "AveragePooling1D",
                node_type= LayerNode,
                logic = LayerNode.layer(layers.AveragePooling1D),
                annotations = {
                        "pool_size": Parameter(AttrType.INPUT, AInteger, default=2),
                        "strides": Parameter(AttrType.INPUT, AInteger, default=2),
                        "padding": Parameter(AttrType.INPUT, AEnum[Padding]),
                    },
                input=LayerNode
            ),
            NodeAnnotation(
                label= "AveragePooling2D",
                node_type= LayerNode,
                logic = LayerNode.layer(layers.AveragePooling2D),
                annotations = {
                        "pool_size": Parameter(AttrType.INPUT, ASequence[AInteger, AInteger], default=(2,2)),
                        "strides": Parameter(AttrType.INPUT, ASequence[AInteger, AInteger], default=(2,2)),
                        "padding": Parameter(AttrType.INPUT, AEnum[Padding]),
                    },
                input=LayerNode
            ),
            NodeAnnotation(
                label= "AveragePooling3D",
                node_type= LayerNode,
                logic = LayerNode.layer(layers.AveragePooling3D),
                annotations = {
                        "pool_size": Parameter(AttrType.INPUT, ASequence[AInteger, AInteger, AInteger], default=(2,2,2)),
                        "strides": Parameter(AttrType.INPUT, ASequence[AInteger, AInteger, AInteger], default=(2,2,2)),
                        "padding": Parameter(AttrType.INPUT, AEnum[Padding]),
                    },
                input=LayerNode
            )
        ],
        "Operations":[
            NodeAnnotation(
                label="Concatenate",
                node_type= LayerNode,
                logic = LayerNode.layer(layers.Concatenate),
                input=LayerNode
            ),
            NodeAnnotation(
                label="Flatten",
                node_type= LayerNode,
                logic = LayerNode.layer(layers.Flatten),
                input=LayerNode
            ),
            NodeAnnotation(
                label="Add",
                node_type= LayerNode,
                logic = LayerNode.layer(layers.Add),
                input=LayerNode
            )
        ]
    },
    "Training": {
        "General": [
            NodeAnnotation(
                label="Compile model",
                node_type= CompileNode,
                logic = CompileNode.compile_model,
                annotations = {
                        "optimizer": Parameter(AttrType.INPUT, AEnum[Optimizers]),
                        "loss": Parameter(AttrType.INPUT, AEnum[Losses]),
                    },
                input=LayerNode
            ),
            NodeAnnotation(
                label="Fit model",
                node_type= FitNode,
                logic = FitNode.fit,
                annotations = {
                        "x": Parameter(AttrType.INPUT, ANode[Single[DataNode]]),
                        "y": Parameter(AttrType.INPUT, ANode[Single[DataNode]]),
                        "epochs": Parameter(AttrType.INPUT, AInteger),
                        "history": Parameter(AttrType.OUTPUT, ANode[DataNode])  
                    },
                input = Single[CompileNode]
            ),
            NodeAnnotation(
                label="Predict",
                node_type= PredictNode,
                logic = PredictNode.predict,
                annotations = {
                        "x": Parameter(AttrType.INPUT, ANode[Single[DataNode]]),
                    },
                input = Single[FitNode],
                output = DataNode
            )
        ],
        "Utils": [
            NodeAnnotation(
                label="Save model",
                node_type= UtilsNode,
                logic = keras.saving.save_model,
                annotations = {
                        "model": Parameter(AttrType.INPUT, ANode[Single[FitNode]]),
                        "filepath": Parameter(AttrType.INPUT, AString, default='model.keras')
                    },
                input = False,
                output = False
            ),
            NodeAnnotation(
                label="Plot model",
                node_type= UtilsNode,
                logic = keras.utils.plot_model,
                annotations = {
                        "model": Parameter(AttrType.INPUT, ANode[Single[CompileNode]]),
                        "to_file": Parameter(AttrType.INPUT, AString),
                        "show_shapes": Parameter(AttrType.INPUT, ABoolean),
                        "show_layer_names": Parameter(AttrType.INPUT, ABoolean),
                        "show_layer_activations": Parameter(AttrType.INPUT, ABoolean)
                    },
                input = False,
                output = False
            ),
            NodeAnnotation(
                label="Calculate Metric",
                node_type=MetricNode,
                logic=MetricNode.calculate,
                annotations={
                    "metric": Parameter(AttrType.INPUT, AEnum[Metrics]),
                    "y_true": Parameter(AttrType.INPUT, ANode[Single[DataNode]]),
                    "y_pred": Parameter(AttrType.INPUT, ANode[Single[DataNode]]),
                    "data": Parameter(
                        AttrType.STATIC,
                        AFloat,
                        backfield=MetricNode.data
                    )
                },
                input=False,
                output=DataNode
            ),
            NodeAnnotation(
                label="Save data",
                node_type = UtilsNode,
                logic = np.savetxt,
                annotations = {
                    "X": Parameter(AttrType.INPUT, ANode[Single[DataNode]]),
                    "fname": Parameter(AttrType.INPUT, AString, default='result.txt')
                },
                input = False,
                output = False
            ),
            NodeAnnotation(
                label="Save model as JSON",
                node_type = UtilsNode,
                logic = UtilsNode.to_json,
                annotations = {
                    "model": Parameter(AttrType.INPUT, ANode[Single[CompileNode]]),
                    "filename": Parameter(AttrType.INPUT, AString, default='model.json')
                },
                input = False,
                output = False
            ),
        ]
    }
}
