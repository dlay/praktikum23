import torch
import torch.nn as nn
import torch.nn.functional as F
import torch.optim as optim
from numpy import ndarray

# Hyperparameters
HIDDEN_LAYER_1 = 16
HIDDEN_LAYER_2 = 32
LEARNING_RATE = 0.01

class Network(nn.Module):
    def __init__(self, input_size: int, n_hidden1: int, n_hidden2: int):
        super(Network, self).__init__()

        output_size = 1
        self.fc1 = nn.Linear(input_size, n_hidden1)
        self.fc2 = nn.Linear(n_hidden1, n_hidden2)
        self.fc3 = nn.Linear(n_hidden2, output_size)

    def forward(self, x):
        x = F.relu(self.fc1(x))
        x = F.relu(self.fc2(x))
        return torch.sigmoid(self.fc3(x))
    
def train(data: ndarray, labels: ndarray, img: ndarray) -> ndarray:
    device=torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    print(f"Training using {device}")

    net = Network(5, HIDDEN_LAYER_1, HIDDEN_LAYER_2).to(device)
    tData = torch.from_numpy(data).float()
    tLabels = torch.from_numpy(labels).float()
    if device.type == 'cuda':
            tData = tData.cuda()
            tLabels = tLabels.cuda()

    optimizer = optim.Adam(net.parameters(), lr = LEARNING_RATE)

    lastLoss = 0
    lossCounter = 10

    # Training loop
    for epoch in range(1000):
        optimizer.zero_grad()
        predict = net(tData)
        loss = F.binary_cross_entropy(predict.squeeze(), tLabels)
        loss.backward()
        if loss.item() == lastLoss:
            if lossCounter == 0:
                return train(data, labels, img)
            lossCounter -= 1
        lastLoss = loss.item()
        optimizer.step()
        if epoch % 100 == 0:
            print(f"Training loss after epoch {epoch}: {loss.item()}")
    print("Training finished.")

    # Input full image in trained network
    net.eval()
    img = torch.from_numpy(img).float()
    with torch.no_grad():
        if device.type == 'cuda':
            img = img.cuda()
        eval = net(img)
        if device.type == 'cuda':
            eval = eval.cpu()
    return eval.numpy()
