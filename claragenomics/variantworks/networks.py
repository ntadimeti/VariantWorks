import torch
import torch.nn as nn

from nemo.backends.pytorch.nm import TrainableNM
from nemo.utils.decorators import add_port_docs
from nemo.core.neural_types import ChannelType, LabelsType, LossType, NeuralType, LogitsType
from nemo.core.neural_factory import DeviceType

class AlexNet(TrainableNM):
    @property
    @add_port_docs()
    def input_ports(self):
        """Returns definitions of module input ports.
        """
        return {
            "pileup": NeuralType(('B', 'C', 'H', 'W'), ChannelType()),
        }

    @property
    @add_port_docs()
    def output_ports(self):
        """Returns definitions of module output ports.
        """
        return {
            'log_probs_vt': NeuralType(('B', 'D'), LogitsType()), # Variant type
            'log_probs_va': NeuralType(('B', 'D'), LogitsType()), # Variant allele
        }

    def __init__(self, num_input_channels, num_vt, num_alleles):
        super().__init__()
        self.num_vt = num_vt
        self.num_input_channels = num_input_channels
        self.num_alleles = num_alleles

        self.features = nn.Sequential(
            nn.Conv2d(self.num_input_channels, 64, kernel_size=11, stride=4, padding=2),
            nn.ReLU(inplace=True),
            nn.MaxPool2d(kernel_size=3, stride=2),
            nn.Conv2d(64, 192, kernel_size=5, padding=2),
            nn.ReLU(inplace=True),
            nn.MaxPool2d(kernel_size=3, stride=2),
            nn.Conv2d(192, 384, kernel_size=3, padding=1),
            nn.ReLU(inplace=True),
            nn.Conv2d(384, 256, kernel_size=3, padding=1),
            nn.ReLU(inplace=True),
            nn.Conv2d(256, 256, kernel_size=3, padding=1),
            nn.ReLU(inplace=True),
            nn.MaxPool2d(kernel_size=3, stride=2),
        )
        self.avgpool = nn.AdaptiveAvgPool2d((6, 6))
        self.common_classifier = nn.Sequential(
            nn.Dropout(),
            nn.Linear(256 * 6 * 6, 4096),
            nn.ReLU(inplace=True),
            nn.Dropout(),
            nn.Linear(4096, 4096),
            nn.ReLU(inplace=True),
            #nn.Linear(4096, self.num_vt),
        )
        self.vt_classifier = nn.Linear(4096, self.num_vt)
        self.va_classifier = nn.Linear(4096, self.num_alleles)

        self._device = torch.device("cuda" if self.placement == DeviceType.GPU else "cpu")
        self.to(self._device)

    def forward(self, pileup):
        pileup = self.features(pileup)
        pileup = self.avgpool(pileup)
        pileup = torch.flatten(pileup, 1)
        pileup = self.common_classifier(pileup)
        vt = self.vt_classifier(pileup)
        va = self.va_classifier(pileup)
        return vt, va