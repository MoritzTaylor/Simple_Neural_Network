import matplotlib.pyplot as plt
from sklearn.datasets import fetch_openml
from tqdm import tqdm

from layers import *
from models import *
from optimizers import *

DATASET = 'mnist_784'
BATCH_SIZE = 32
LR = 0.0001
HIDDEN_SIZE = 100
OUTPUT_SIZE = 10
TRAIN_ITERATIONS = 1500

if __name__ == '__main__':
    # Fetch training data: MNIST
    print(f'Fetching training data: {DATASET}')
    dataset = fetch_openml(DATASET)
    X, y = dataset["data"], dataset["target"]
    X = X.reshape(X.shape[0], 28, 28)
    y = y.astype(np.uint8)

    if len(X.shape) == 3:
        # If images are grayscale, there is no channel axis
        X = X[..., np.newaxis]

    # Split data in training and test set
    m_train = 60000
    m_test = X.shape[0] - m_train
    X_train, X_test = X[:m_train] / 255.0, X[m_train:] / 255.0
    y_train, y_test = y[:m_train], y[m_train:]

    # Define the network parameters
    hidden_size, output_size = HIDDEN_SIZE, OUTPUT_SIZE
    num_kernels = 32

    # Define the network layer by layer
    print(f'Defining model: '
          f'CNN with '
          f'Conv7x7 -> MaxPool2D -> Flatten -> Dense({hidden_size}) -> Dense({output_size}) -> CategoricalCrossEntropy')
    model = Model(loss='crossentropy')
    layer1 = Conv2D(filter_size=7, num_kernels=num_kernels, input_depth=1,
                    stride=1, dilation=0, padding='same',
                    activation='relu', initializer='xavier',
                    regularization=1e-3)
    model.add_layer(layer1)

    layer2 = MaxPool2D(pool_size=4, stride=1)
    model.add_layer(layer2)

    layer3 = Flatten()
    model.add_layer(layer3)

    # TODO: Detect input size for the layer automatically
    layer4 = Dense(input_size=25088, output_size=hidden_size,
                   activation='relu', initializer='xavier',
                   regularization=1e-3)
    model.add_layer(layer4)

    layer5 = Dense(input_size=hidden_size, output_size=output_size,
                   activation='linear', initializer='xavier',
                   regularization=1e-3)
    model.add_layer(layer5)

    optim = SGD(lr=LR)
    model.add_optim(optimizer=optim)

    # Training
    print(f'Training CNN on MNIST')
    cache_loss = list()
    cache_acc = list()
    collect_loss = list()
    collect_acc = list()
    iterations = list()
    for iteration in tqdm(range(TRAIN_ITERATIONS)):
        # Training the network and observing the loss
        batch_x, batch_y = shuffle_batch(X_train, y_train, batch_size=BATCH_SIZE)
        loss, acc = model.train(batch_x, batch_y)
        cache_loss.append(loss)
        cache_acc.append(acc)

        if (iteration + 1) % 100 == 0 or iteration == 0:
            mean_loss = np.mean(cache_loss)
            mean_acc = np.mean(acc)
            print(f'Iteration: {iteration + 1}, '
                  f'Average Train Loss: {mean_loss}, '
                  f'Average Train Accuracy: {mean_acc * 100}%')
            iterations.append(iteration + 1)
            collect_loss.append(mean_loss)
            collect_acc.append(mean_acc)
            cache_loss = list()
            cache_acc = list()

    fig, ax = plt.subplots()
    ax.plot(iterations, collect_loss, label="train")
    ax.set(xlabel='iteration', ylabel='loss')
    ax.legend()
    ax.grid()
    fig.savefig('results/conv_mnist_classification_simple_loss.png')
    plt.show()

    fig, ax = plt.subplots()
    ax.plot(iterations, collect_acc, label="train")
    ax.set(xlabel='iteration', ylabel='accuracy')
    ax.legend()
    ax.grid()
    fig.savefig('results/conv_mnist_classification_simple_acc.png')
    plt.show()

    model.set_eval()
    i, j = 0, 0
    idx = np.random.choice(X_test.shape[0], 15, replace=False)
    for k in idx:
        digit = X_test[k]
        label = y_test[k]
        prediction = model(digit[np.newaxis])
        ax = plt.subplot2grid((3, 5), (i, j))
        ax.set_title(f"Pred.: {str(np.argmax(prediction))}")
        plt.axis('off')
        plt.imshow(digit[..., 0])
        j += 1
        if j % 5 == 0:
            i += 1
            j = 0
    #plt.savefig('results/conv_mnist_classification_simple_vis_pred.png')
    plt.show()
