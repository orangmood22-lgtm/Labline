"""ToyClassifier with channel attention — DELIBERATELY CONTAINS A DEAD CODE PATH.

The attention module is defined but BYPASSED in forward().
This is an intentional bug for the e2e drill: the model always falls
back to the baseline MLP path, making the "novel" component a no-op.
"""

import torch
import torch.nn as nn


class ChannelAttention(nn.Module):
    """Lightweight channel attention module (squeeze-and-excite style)."""

    def __init__(self, in_features: int, bottleneck: int = 64):
        super().__init__()
        self.squeeze = nn.Linear(in_features, bottleneck)
        self.excite = nn.Linear(bottleneck, in_features)
        self.sigmoid = nn.Sigmoid()

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        weights = self.sigmoid(self.excite(torch.relu(self.squeeze(x))))
        return x * weights


class ToyClassifier(nn.Module):
    """MLP + channel attention for CIFAR-10.

    BUG (intentional): The attention module is instantiated but never
    used in forward().  The forward path is identical to BaselineMLP.
    """

    def __init__(self, input_dim: int = 3072, hidden_dim: int = 256,
                 num_classes: int = 10, attention_bottleneck: int = 64):
        super().__init__()
        self.fc1 = nn.Linear(input_dim, hidden_dim)
        self.fc2 = nn.Linear(hidden_dim, hidden_dim)
        self.fc3 = nn.Linear(hidden_dim, num_classes)
        self.relu = nn.ReLU()

        # Attention module is DEFINED …
        self.attention = ChannelAttention(hidden_dim, attention_bottleneck)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = self.relu(self.fc1(x))
        # === DEAD PATH — attention is NOT applied ===
        # Should be:  x = self.attention(x)
        # But we skip it, so ToyClassifier == BaselineMLP in behaviour.
        x = self.relu(self.fc2(x))
        x = self.fc3(x)
        return x
