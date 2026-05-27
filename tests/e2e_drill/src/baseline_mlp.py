"""BaselineMLP — simple 3-layer MLP for CIFAR-10 classification."""

import torch
import torch.nn as nn


class BaselineMLP(nn.Module):
    """Plain MLP baseline for CIFAR-10 (no attention, no novelty)."""

    def __init__(self, input_dim: int = 3072, hidden_dim: int = 256,
                 num_classes: int = 10):
        super().__init__()
        self.fc1 = nn.Linear(input_dim, hidden_dim)
        self.fc2 = nn.Linear(hidden_dim, hidden_dim)
        self.fc3 = nn.Linear(hidden_dim, num_classes)
        self.relu = nn.ReLU()

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = self.relu(self.fc1(x))
        x = self.relu(self.fc2(x))
        x = self.fc3(x)
        return x
