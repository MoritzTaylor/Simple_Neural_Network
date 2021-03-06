import numpy as np
from initializers import get_initializer
from activations import get_activation
from utils import *


class Layer:

    def __init__(self, activation=None, initializer=None, regularization=0.0):
        self.X = None
        self.train = True
        self.reg = regularization
        self.add_activation(activation)
        self.add_initializer(initializer)

    def __call__(self, x):
        return self.forward_pass(x)

    def __repr__(self):
        raise NotImplementedError

    def forward_pass(self, x):
        raise NotImplementedError

    def backward_pass(self, dL_dy):
        raise NotImplementedError

    def _gradients(self, dL_dy):
        raise NotImplementedError

    def set_train(self):
        self.train = True
    
    def set_eval(self):
        self.train = False

    def add_initializer(self, initializer):
        self._initializer = get_initializer(initializer)

    def add_activation(self, activation_func):
        self._activation = get_activation(activation_func)
    
    def add_optim(self, optimizer):
        self._optimizer = optimizer


class Flatten(Layer):
    """
    Takes a multidimensional Numpy-Array as input and returns a vectorized form of it
    to pass it to a fully connected/dense layer
    """

    def __repr__(self):
        return f"Flattening Layer"

    def __init__(self):
        super().__init__()
        self._in_shape = None

    def forward_pass(self, x):
        self.X = x
        self._in_shape = x.shape
        batch_size = x.shape[0]
        return x.reshape(batch_size, -1)

    def backward_pass(self, dL_dy):
        return dL_dy.reshape(self._in_shape)


class Dense(Layer):
    """
    A regular neural network layer, this means a layer in which every unit is 
    connected to every unit of the previous layer.

    The output is computed as follow:
        z = x dot W + b
        true_val = activation(z)

        x should have shape of (batch_size, #inputs == #units)
        true_val should have shape of (batch_size, #outputs)


    Arguments:
        input_size: Length of the flattend input vector as integer
        output_size: Number of units of this layer, which is the same of the output size
        activation: Activation function to use in the computation
        initializer: Weight initializers to set the values of the weights and biases
    """

    def __repr__(self):
        return f"Dense Layer; " \
               f"Shape of weights: {self.W.shape}"

    def __init__(self, input_size, output_size,
                 activation='linear', initializer='xavier', regularization=0.0):
        super().__init__(activation=activation, initializer=initializer, regularization=regularization)
        self.b = self._initializer((1, output_size))  # weight shape: (output_size, )
        self.W = self._initializer((input_size, output_size))  # weight shape: (input_depth, output_size)

    def forward_pass(self, x):
        self.X = x
        z = x @ self.W + self.b
        y = self._activation.calc(z=z)
        return y

    def backward_pass(self, dL_dy):
        """
        Computes the backward pass of the layer.

        Arguments:
            dL_dy: Gradient tensor of the following layer
        """
        assert self.train, 'Layer not set to train!'
        assert self.X is not None, 'No forward pass before!'

        dx, dw, db = self._gradients(dL_dy)

        dw += self.reg * self.W
        db += self.reg * self.b

        m = self.X.shape[0]
        self.W -= self._optimizer(dw, self.W) * (1/m)
        self.b -= self._optimizer(db, self.b) * (1/m)

        return dx

    def _gradients(self, dL_dy):
        """
        Computes the gradients of the weights, biases und the input
        w.r.t to the weights, biases and inputs

        Arguments:
            dL_dy: Gradient tensor from the following layer
        """
        dL_dz = dL_dy * self._activation.derivative()
        dL_dx = dL_dz @ self.W.T
        dL_dw = self.X.T @ dL_dz
        dL_db = np.sum(dL_dz, axis=0, keepdims=True)
        return dL_dx, dL_dw, dL_db


class Conv2D(Layer):

    def __init__(self, filter_size, num_kernels, input_depth, stride=1, dilation=0, padding='same',
                 activation='relu', initializer='xavier', regularization=0.0):
        super().__init__(activation=activation, initializer=initializer, regularization=regularization)
        self.b = self._initializer((1, 1, 1, num_kernels))
        kernel_shape = (filter_size, filter_size, input_depth, num_kernels)
        self.W = self._initializer(kernel_shape)
        self.pad = get_padding(kernel_shape, padding)  # tuple storing two single tuple
        self.stride = stride
        self.dilation = dilation

    def __repr__(self):
        return f"Convolution Layer; " \
               f"Kernel shape: {self.W.shape}; " \
               f"Padding: {self.pad}; " \
               f"Stride: {self.stride}; " \
               f"Dilation: {self.dilation}"
    
    def forward_pass(self, x):
        """
        Returns the output of the convolution after activation

        Arguments:
            `x`: is a NumPy array of shape [batch_size, height, width, n_input_channels]
        `weights` has shape [filter_height, filter_width, n_features_in, n_features_out]
        `biases` has shape [n_output_channels]

        """
        # TODO: Add more comments
        # TODO: Testing
        self.X = x

        z = conv2d(x, self.W, self.b, self.pad, self.stride, self.dilation)
        y = self._activation.calc(z=z)
        return y

    def backward_pass(self, dL_dy):
        """
        Computes the backward pass of the layer.

        Arguments:
            dL_dy: Gradient tensor of the following layer
        """
        assert self.train, 'Layer not set to train!'
        assert self.X is not None, 'No forward pass before!'

        dx, dw, db = self._gradients(dL_dy)

        dw += self.reg * self.W
        db += self.reg * self.b

        m = self.X.shape[0]  # Determine batch size
        self.W -= self._optimizer(dw, self.W) * (1/m)
        self.b -= self._optimizer(db, self.b) * (1/m)

        return dx

    def _gradients(self, dL_dy):
        """
        Computes the gradients of the weights, biases und the input
        w.r.t to the weights, biases and inputs

        Arguments:
            dL_dy: Gradient tensor of the following layer
        """
        # TODO: Add more comments
        # TODO: Testing

        filter_height, filter_width, in_channels, out_channels = self.W.shape
        batch_size, out_height, out_width, _ = dL_dy.shape

        # Calculating gradient before activation
        dL_dz = dL_dy * self._activation.derivative()

        # columnize W, X, and dL_dz
        W_col = self.W.transpose(3, 2, 0, 1).reshape(out_channels, -1).T
        x_reshaped = self.X.transpose(0, 3, 1, 2)
        x_col = image_to_column(x_reshaped, self.W.shape, self.stride, self.pad, self.dilation)
        dL_dz_col = dL_dz.transpose(3, 1, 2, 0).reshape(out_channels, -1)

        # Calculating gradient dL_dx of input x
        dL_dx = W_col @ dL_dz_col
        dL_dx = column_to_image(dL_dx, self.X.shape, self.W.shape, self.stride, self.pad, self.dilation)
        dL_dx = dL_dx.transpose(0, 2, 3, 1)

        # Calculating gradient dL_dw of weights W
        dL_dw = dL_dz_col @ x_col.T
        dL_dw = dL_dw.reshape(out_channels, in_channels, filter_height, filter_width)
        #filter_height, in_channels, filter_width, out_channels,
        dL_dw = dL_dw.transpose(2, 3, 1, 0)

        # Calculating gradient dL_db of bias b
        dL_db = np.sum(dL_dz_col, axis=1)#np.sum(dL_dz_col, axis=1)
        dL_db = dL_db.reshape(1, 1, 1, -1)#dL_db.reshape(1, -1)

        return dL_dx, dL_dw, dL_db


class MaxPool2D(Layer):

    def __init__(self, pool_size, stride=1, padding='same'):
        self.X = None
        self.train = True
        self.stride = stride
        self.pool_size = pool_size
        self.padding = get_padding((pool_size, pool_size), padding)

    def __repr__(self):
        return f"MaxPool Layer; " \
               f"Pool shape: {self.pool_size}x{self.pool_size}; " \
               f"Stride: {self.stride}"

    def forward_pass(self, x):
        """
        Max pooling

        Arguments:
            `x` is a numpy array of shape [batch_size, height, width, n_features]
        """
        self.X = x
        out, self.X_col, self.X_argmax = pool(x, np.max, self.pool_size, self.padding, self.stride)
        return out

    def forward_pass_naive(self, x):
        """
        Max pooling

        Arguments:
            `x` is a numpy array of shape [batch_size, height, width, n_features]
        """
        # TODO: Add more comments
        # TODO: Testing
        batch_size, input_height, input_width, in_channels = x.shape

        output_height = (input_height - self.pool_size)//self.stride + 1
        output_width = (input_width - self.pool_size)//self.stride + 1

        result = np.zeros((batch_size, output_height, output_width, in_channels))
        # TODO: Refactor to more efficient method instead of naive one
        for m in range(batch_size):
            for i in range(output_height):
                for j in range(output_width):
                    for c in range(in_channels):
                        k, l = i * self.stride, j * self.stride
                        result[m, i, j, c] = np.max(x[m, k:(k + self.pool_size), l: (l + self.pool_size), c])

        return result

    def backward_pass(self, dL_dy):
        batch_size, in_height, in_width, channels = self.X.shape
        pool_height, pool_width = (self.pool_size, self.pool_size)
        stride = self.stride
        padding = self.padding

        out_height = (in_height - pool_height) // stride + 1
        out_width = (in_width - pool_width) // stride + 1

        dout_reshaped = dL_dy.transpose(1, 2, 0, 3).flatten()
        dx_cols = np.zeros_like(self.X_col)
        dx_cols[self.X_argmax, np.arange(dx_cols.shape[1])] = dout_reshaped
        dL_dx = column_to_image(dx_cols, (batch_size * channels, 1, in_height, in_width), (pool_height, pool_width),
                                stride, padding)
        dL_dx = dL_dx.reshape((batch_size, channels, in_height, in_width))
        dL_dx = dL_dx.transpose(0, 2, 3, 1)

        return dL_dx


class AveragePool2D(Layer):

    def __repr__(self):
        return f"MaxPool Layer; " \
               f"Pool shape: {self.pool_size}; " \
               f"Stride: {self.stride}"

    def __init__(self, pool_size, stride):
        self.X = None
        self.train = True
        self.stride = stride
        self.pool_size = pool_size

    def forward_pass(self, x):
        """
        Average pooling

        Arguments:
            `x` is a numpy array of shape [batch_size, height, width, n_features]
        """
        # TODO: Add more comments
        # TODO: Testing

        self.X = x
        batch_size, input_height, input_width, in_channels = x.shape

        output_height = (input_height - self.pool_size) // self.stride + 1
        output_width = (input_width - self.pool_size) // self.stride + 1

        result = np.zeros((batch_size, output_height, output_width, in_channels))
        # TODO: Refactor to more efficient method instead of naive one
        for m in range(batch_size):
            for i in range(output_height):
                for j in range(output_width):
                    for c in range(in_channels):
                        k, l = i * self.stride, j * self.stride
                        result[m, i, j, c] = np.average(x[m, k:(k + self.pool_size), l: (l + self.pool_size), c])

        return result

    def backward_pass(self, dL_dy):
        # TODO
        pass


class BatchNorm(Layer):

    def __init__(self, input_size, output_size,
                 activation='linear', initializer='xavier', regularization=0.0):
        super().__init__(activation=activation, initializer=initializer, regularization=regularization)
        self.beta = self._initializer((1, output_size))  # weight shape: (output_size, )
        self.gamma = self._initializer((input_size, output_size))  # weight shape: (input_depth, output_size)
        self.mu_cache = list()
        self.sig_cache = list()
        self.mu_inference = 0
        self.sig_inference = 0

    def forward_pass(self, x):
        self.X = x
        if self.train:
            mu = np.mean(x, axis=0)
            sig = np.var(x, axis=0)
            self.mu_cache.append(mu)
            self.sig_cache.append(sig)
            self.mu_inference = incremental_mean(self.mu_inference, mu, len(self.mu_cache))
            self.sig_inference = incremental_mean(self.sig_inference, sig, len(self.sig_cache))
        else:
            # If we are in inference/testing mode, we must use derived mean and variance,
            # since no mini batches are available anymore.
            mu = self.mu_inference
            sig = self.sig_inference

        x_norm = (x - mu) / np.sqrt(sig + 1e-8)
        out = self.gamma * x_norm + self.beta

        return out

    def backward_pass(self, dL_dy):
        """
        Computes the backward pass of the layer.

        Arguments:
            dL_dy: Gradient tensor of the following layer
        """
        assert self.train, 'Layer not set to train!'
        assert self.X is not None, 'No forward pass before!'

        dx, dw, db = self._gradients(dL_dy)

        dw += self.reg * self.gamma
        db += self.reg * self.beta

        m = self.X.shape[0]  # Determine batch size
        self.gamma -= (1 / m) * self._optimizer(dw, self.W)
        self.beta -= (1 / m) * self._optimizer(db, self.b)

        return dx

    def _gradients(self, dL_dy):
        dL_dz = dL_dy * self._activation.derivative()
        dL_dx = dL_dz @ self.gamma.T
        dL_dw = self.X.T @ dL_dz
        dL_db = np.sum(dL_dz, axis=0, keepdims=True)
        return dL_dx, dL_dw, dL_db




