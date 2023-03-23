// @ts-ignore
import { Request, Response } from 'express';

export default {
  'POST /api/v1/processes/suicide': (req: Request, res: Response) => {
    res.status(200).send({
      code: 83,
      data: null,
      msg: '想具心率期头达研产正确转维题。',
      success: true,
    });
  },
};
