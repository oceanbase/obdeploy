// @ts-ignore
import { Request, Response } from 'express';

export default {
  'GET /api/v1/deployments/:name/destroy': (req: Request, res: Response) => {
    res.status(200).send({
      code: 98,
      data: {
        total: 100,
        finished: 88,
        current: '农商江持连无马年布属果下划响问参。',
        status: 'processing',
        msg: '战整青它指强容张太矿速维种着在按始广。',
        info: [
          {
            component: '技办边山思边济反动务完由。',
            status: 'processing',
            result: '造就基资心节美志消路原天放业重清。',
          },
          {
            component: '济政见为给般动我强人价化白委值法等。',
            status: 'error',
            result: '增军红说展着连一率别标山五同人度。',
          },
        ],
      },
      msg: '利党办们南小交查组连法难空。',
      success: false,
    });
  },
};
