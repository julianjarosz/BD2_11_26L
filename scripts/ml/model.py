import torch
import torch.nn as nn

class PollutionLSTM(nn.Module):
    def __init__(self, input_size, hidden_size, num_layers, output_size, future_days):
        super(PollutionLSTM, self).__init__()
        self.hidden_size = hidden_size
        self.num_layers = num_layers
        self.future_days = future_days
        self.output_size = output_size

        self.lstm = nn.LSTM(input_size, hidden_size, num_layers, batch_first=True)
        # we predict future_days * output_size values and then reshape
        self.fc = nn.Linear(hidden_size, future_days * output_size)

    def forward(self, x):
        # x shape: (batch_size, sequence_length, input_size)
        # initialize hidden state and cell state with zeros
        h0 = torch.zeros(self.num_layers, x.size(0), self.hidden_size).to(x.device)
        c0 = torch.zeros(self.num_layers, x.size(0), self.hidden_size).to(x.device)

        # forward propagate LSTM
        out, _ = self.lstm(x, (h0, c0))

        # decode the hidden state of the last time step
        out = self.fc(out[:, -1, :])

        # reshape to (batch_size, future_days, output_size)
        out = out.view(-1, self.future_days, self.output_size)
        return out
