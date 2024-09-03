// @ts-ignore
import { Request, Response } from 'express';

export default {
  'POST /api/v1/component_change/:name': (req: Request, res: Response) => {
    res
      .status(200)
      .send({ code: 97, data: null, msg: '声得意于去于理力化应便该西识效起些。', success: false });
  },
};
